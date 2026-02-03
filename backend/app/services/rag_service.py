# app/services/rag_service.py 完整替换

import os, shutil, time, logging, re, httpx, redis, json, hashlib, asyncio
from sqlalchemy.orm import Session
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.services.config_service import ConfigService
from app.services.tool_service import ToolService
from app.core.prompts import INTENT_DISPATCH_PROMPT, RAG_SYSTEM_PROMPT

os.environ["ANONYMIZED_TELEMETRY"] = "False"
logger = logging.getLogger("RAGService")


class AliyunEmbeddingWrapper(Embeddings):
    def __init__(self, model, api_key, base_url):
        self.model, self.api_key = model, api_key
        self.url = base_url.replace("/compatible-mode/v1", "/compatible-mode/v1/embeddings")

    def embed_documents(self, texts):
        results = []
        with httpx.Client(timeout=60.0) as client:
            for i in range(0, len(texts), 10):
                batch = [str(t) for t in texts[i: i + 10]]
                resp = client.post(self.url, json={"model": self.model, "input": batch},
                                   headers={"Authorization": f"Bearer {self.api_key}"})
                results.extend([item["embedding"] for item in resp.json()["data"]])
        return results

    def embed_query(self, text): return self.embed_documents([text])[0]


class RAGService:
    def __init__(self, db: Session):
        emb_cfg = ConfigService.get_active_config(db, "embedding")
        llm_cfg = ConfigService.get_active_config(db, "llm")
        self.custom_embeddings = AliyunEmbeddingWrapper(emb_cfg.model_name, emb_cfg.api_key, emb_cfg.base_url)
        self.llm = ChatOpenAI(model=llm_cfg.model_name, openai_api_key=llm_cfg.api_key,
                              openai_api_base=llm_cfg.base_url, temperature=0, streaming=True)
        self.index_path = os.path.abspath(os.path.join(settings.BASE_DIR, "data", "faiss_index"))
        self.vector_db = None
        if os.path.exists(os.path.join(self.index_path, "index.faiss")):
            self.vector_db = FAISS.load_local(self.index_path, self.custom_embeddings,
                                              allow_dangerous_deserialization=True)
        try:
            self.redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0,
                                            decode_responses=True)
        except:
            self.redis_client = None

    def strict_clean(self, text: str) -> str:
        return re.sub(r'\s+', ' ', "".join(c for c in text if c.isprintable())).strip() if text else ""

    def ingest_pdf(self, file_upload_object, filename: str) -> int:
        upload_path = os.path.join(settings.BASE_DIR, "data", "uploads")
        os.makedirs(upload_path, exist_ok=True)
        file_save_path = os.path.join(upload_path, filename)
        with open(file_save_path, "wb") as buffer:
            shutil.copyfileobj(file_upload_object.file, buffer)
        loader = PyPDFLoader(file_save_path)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=450, chunk_overlap=100)
        valid_texts = [self.strict_clean(doc.page_content) for doc in text_splitter.split_documents(loader.load()) if
                       len(doc.page_content) > 10]
        if self.vector_db is None:
            self.vector_db = FAISS.from_texts(valid_texts, self.custom_embeddings)
        else:
            self.vector_db.add_texts(valid_texts)
        os.makedirs(self.index_path, exist_ok=True)
        self.vector_db.save_local(self.index_path)
        return len(valid_texts)

    async def chat_stream(self, query: str, session_id: str = "default"):
        # --- 1. 意图分拣 (Intent Dispatching) ---
        dispatch_msg = INTENT_DISPATCH_PROMPT.format(query=query)
        try:
            # 这里的 llm 调用建议不开启 streaming，因为我们要处理 JSON 逻辑
            intent_res = self.llm.invoke(dispatch_msg)
            # 提取 JSON（防止 AI 话多带了前缀）
            json_match = re.search(r'\{.*\}', intent_res.content, re.DOTALL)
            intent_obj = json.loads(json_match.group()) if json_match else {"intent": "LEGAL_QUERY"}

            # 分支路由
            if intent_obj["intent"] == "NAVIGATION":
                p = intent_obj.get("params", {})
                yield json.dumps({"type": "content", "data": f"🔄 **正在为您规划 {p.get('mode', '驾车')} 路线...**\n\n"})
                route_info = await ToolService.get_route_plan(p.get('from'), p.get('to'), p.get('mode', 'driving'))
                yield json.dumps({"type": "content", "data": route_info})
                yield json.dumps({"type": "done"});
                return

            elif intent_obj["intent"] == "CHITCHAT":
                yield json.dumps(
                    {"type": "content", "data": "您好！我是您的智能交通助手。您可以问我‘交通法规咨询’或‘出行路径规划’。"})
                yield json.dumps({"type": "done"});
                return

            elif intent_obj["intent"] == "INVALID":
                yield json.dumps({"type": "content", "data": "抱歉，我只能处理与交通、出行和法律相关的内容。请重新输入。"})
                yield json.dumps({"type": "done"});
                return
        except Exception as e:
            logger.error(f"Intent Error: {e}")  # 分拣失败则默认往下走 RAG

        # --- 2. 专家 RAG 流程 ---
        # 检索依据
        docs_with_scores = self.vector_db.similarity_search_with_score(query, k=6)
        filtered_docs = [doc for doc, score in docs_with_scores if score < 0.85]

        if not filtered_docs:
            yield json.dumps({"type": "content", "data": "抱歉，在知识库中未找到相关法律依据。建议咨询人工客服。"})
            yield json.dumps({"type": "done"});
            return

        sources = [doc.page_content for doc in filtered_docs]
        yield json.dumps({"type": "sources", "data": sources})

        # 组织上下文和历史
        context = "\n".join([f"[依据{i + 1}]: {d.page_content}" for i, d in enumerate(filtered_docs)])
        history_str = ""  # 可从 Redis 获取逻辑保持不变

        # 使用专家 Prompt
        final_prompt = RAG_SYSTEM_PROMPT.format(
            context=context,
            history=history_str,
            query=query
        )

        async for chunk in self.llm.astream(final_prompt):
            if chunk.content:
                yield json.dumps({"type": "content", "data": chunk.content}, ensure_ascii=False)

        yield json.dumps({"type": "done"})