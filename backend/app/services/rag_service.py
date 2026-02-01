import os
import shutil
import time
import logging
import re
import httpx
import redis
import json
import hashlib
from sqlalchemy.orm import Session
from typing import List, Dict, Tuple

from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.services.config_service import ConfigService

os.environ["ANONYMIZED_TELEMETRY"] = "False"
logger = logging.getLogger(__name__)


class AliyunEmbeddingWrapper(Embeddings):
    def __init__(self, model, api_key, base_url):
        self.model = model
        self.api_key = api_key
        self.url = base_url.replace("/compatible-mode/v1", "/compatible-mode/v1/embeddings")

    def embed_documents(self, texts):
        embeddings = []
        batch_size = 10
        with httpx.Client(timeout=60.0) as client:
            for i in range(0, len(texts), batch_size):
                batch = [str(t) for t in texts[i: i + batch_size]]
                payload = {"model": self.model, "input": batch}
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                resp = client.post(self.url, json=payload, headers=headers)
                if resp.status_code != 200:
                    raise Exception(f"API Error: {resp.text}")
                data = resp.json()
                embeddings.extend([item["embedding"] for item in data["data"]])
        return embeddings

    def embed_query(self, text):
        return self.embed_documents([text])[0]


class RAGService:
    def __init__(self, db: Session):
        self.db = db
        emb_cfg = ConfigService.get_active_config(db, "embedding")
        llm_cfg = ConfigService.get_active_config(db, "llm")
        if not emb_cfg or not llm_cfg:
            raise Exception("AI 配置缺失")

        self.custom_embeddings = AliyunEmbeddingWrapper(emb_cfg.model_name, emb_cfg.api_key, emb_cfg.base_url)
        # 针对对话压缩和问答分别初始化
        self.llm = ChatOpenAI(
            model=llm_cfg.model_name,
            openai_api_key=llm_cfg.api_key,
            openai_api_base=llm_cfg.base_url,
            temperature=0
        )

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
        if not text: return ""
        text = "".join(c for c in text if c.isprintable())
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def ingest_pdf(self, file_upload_object, filename: str) -> int:
        print(f"\n🚀 [FAISS] 开始处理知识库文档: {filename}")
        upload_path = os.path.join(settings.BASE_DIR, "data", "uploads")
        os.makedirs(upload_path, exist_ok=True)
        file_save_path = os.path.join(upload_path, filename)
        with open(file_save_path, "wb") as buffer:
            shutil.copyfileobj(file_upload_object.file, buffer)

        loader = PyPDFLoader(file_save_path)
        documents = loader.load()

        # --- 优化点：缩小块大小，增加重叠度 ---
        # 这样可以确保长法条（如第九十一条）的背景信息和具体罚则在多个块中都有重叠
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=450,
            chunk_overlap=120,
            separators=["\n\n", "\n", "。", "；", " ", ""]
        )
        splits = text_splitter.split_documents(documents)

        valid_texts = [self.strict_clean(doc.page_content) for doc in splits if
                       len(self.strict_clean(doc.page_content)) > 10]

        if self.vector_db is None:
            self.vector_db = FAISS.from_texts(valid_texts, self.custom_embeddings)
        else:
            self.vector_db.add_texts(valid_texts)

        os.makedirs(self.index_path, exist_ok=True)
        self.vector_db.save_local(self.index_path)
        print(f"✅ 知识库更新完成，有效切片数: {len(valid_texts)}")
        return len(valid_texts)

    def chat(self, query: str, session_id: str = "default"):
            print(f"\n{'-' * 50}\n[新请求] 用户提问: {query}")
            if self.vector_db is None:
                return "知识库为空，请先上传PDF。", []

            query = self.strict_clean(query)
            history_key = f"chat_history:{session_id}"
            history = []
            if self.redis_client:
                history_raw = self.redis_client.get(history_key)
                if history_raw: history = json.loads(history_raw)

            # 1. 查询压缩逻辑 (保持不变)
            search_query = query
            if history:
                history_str = "\n".join(
                    [f"{'用户' if i % 2 == 0 else '助手'}: {msg}" for i, msg in enumerate(history[-4:])])
                rewrite_prompt = f"根据历史对话和当前提问，写一个用于搜索法律库的完整关键词语句。当前提问：{query}\n历史：{history_str}\n仅输出搜索语句。"
                try:
                    rewrite_res = self.llm.invoke(rewrite_prompt)
                    search_query = rewrite_res.content.strip().strip('"')
                    print(f"[上下文改写] 检索词: {search_query}")
                except:
                    pass

            # 2. 检索增强 (增加 K 值)
            # 将 k 提高到 8，这样能把第九十一条的相关切片全部找齐
            docs_with_scores = self.vector_db.similarity_search_with_score(search_query, k=8)

            filtered_docs = []
            for doc, score in docs_with_scores:
                # 这里的阈值需要根据 text-embedding-v4 实测调整
                # 如果 AI 回答“不知道”，可以尝试把 0.8 改大到 0.9
                if score < 0.85:
                    filtered_docs.append(doc)

            if not filtered_docs:
                return "抱歉，知识库中未查阅到相关法律条款，无法给出准确回答。", []

            sources = [doc.page_content for doc in filtered_docs]
            context = "\n\n".join([f"[资料{i + 1}]: {doc.page_content}" for i, doc in enumerate(filtered_docs)])

            # 3. 终极提示词 (极其强调准确性和完整性)
            system_prompt = f"""你是一个法律问答机器人，你的回答必须严格遵守以下规则：
    1. 只能根据提供的【资料】回答。
    2. 回答必须极其完整。例如，如果资料里提到了“营运车辆”，你必须把对应的拘留天数、罚款金额全部列出。
    3. 必须在每个关键段落末尾标注来源，如 [依据1]。
    4. 如果资料中没有直接答案，请诚实回答不知道，严禁编造法律。

    【资料内容】:
    {context}

    【用户提问】:
    {query}
    """
            try:
                res_obj = self.llm.invoke(system_prompt)
                answer = res_obj.content

                if self.redis_client:
                    history.extend([query, answer])
                    self.redis_client.setex(history_key, 1800, json.dumps(history[-10:]))

                print(f"✅ 回答生成完毕")
                return answer, sources
            except Exception as e:
                return f"服务异常: {str(e)}", []