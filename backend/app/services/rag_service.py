# app/services/rag_service.py 完整修复版

import httpx
import json
import logging
import os
import re
import redis
import shutil
from typing import List
import jieba
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from app.core.config import settings
from app.core.prompts import INTENT_DISPATCH_PROMPT, RAG_SYSTEM_PROMPT, QUERY_REWRITE_PROMPT
from app.models import User
from app.models.knowledge import KnowledgeDoc
from app.services.cache_service import CacheManager
from app.services.config_service import ConfigService
from app.services.tool_service import ToolService

os.environ["ANONYMIZED_TELEMETRY"] = "False"
logger = logging.getLogger("RAGService")


class AliyunEmbeddingWrapper(Embeddings):
    def __init__(self, model, api_key, base_url):
        self.model, self.api_key = model, api_key
        self.url = base_url.replace("/compatible-mode/v1", "/compatible-mode/v1/embeddings")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        results = []
        with httpx.Client(timeout=60.0) as client:
            for i in range(0, len(texts), 10):
                batch = [str(t) for t in texts[i: i + 10]]
                payload = {"model": self.model, "input": batch}
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                resp = client.post(self.url, json=payload, headers=headers)
                if resp.status_code != 200:
                    raise Exception(f"Embedding API Error: {resp.text}")
                data = resp.json()
                results.extend([item["embedding"] for item in data["data"]])
        return results

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


class AliyunReranker:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.url = base_url.replace("/compatible-mode/v1", "/ranking/v1/rerank")

    def rerank(self, query: str, documents: List[str]) -> List[int]:
        payload = {"model": "text-rerank-v1", "query": query, "documents": documents, "top_n": 5}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            resp = httpx.post(self.url, json=payload, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                results = resp.json()['results']
                return [r['index'] for r in results]
            return list(range(len(documents)))
        except:
            return list(range(len(documents)))


class RAGService:
    def __init__(self, db: Session, current_user: User = None):
        self.db = db

        # 1. 基础系统配置
        emb_cfg = ConfigService.get_active_config(db, "embedding")
        llm_cfg = ConfigService.get_active_config(db, "llm")
        if not emb_cfg or not llm_cfg:
            raise Exception("AI 配置缺失，请在数据库中配置好模型")

        # 2. 初始化 Redis (必须在 CacheManager 之前)
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=0,
                decode_responses=True
            )
        except:
            self.redis_client = None

        # --- 关键修复：补全 self.cache ---
        self.cache = CacheManager(self.redis_client)

        # 3. 提取用户偏好 & 初始化模型 (你的原有逻辑保持不变)
        user_prefs = {}
        if current_user and current_user.ai_preferences:
            user_prefs = current_user.ai_preferences

        final_llm_model = user_prefs.get("llm_model") or llm_cfg.model_name
        final_llm_key = user_prefs.get("llm_key") or llm_cfg.api_key
        final_emb_model = user_prefs.get("embed_model") or emb_cfg.model_name
        final_emb_key = user_prefs.get("embed_key") or emb_cfg.api_key
        llm_base_url = "https://api.deepseek.com" if "deepseek" in final_llm_model else "https://dashscope.aliyuncs.com/compatible-mode/v1"

        self.custom_embeddings = AliyunEmbeddingWrapper(final_emb_model, final_emb_key, emb_cfg.base_url)
        self.reranker = AliyunReranker(final_emb_key, emb_cfg.base_url)

        self.llm = ChatOpenAI(
            model=final_llm_model,
            openai_api_key=final_llm_key,
            openai_api_base=llm_base_url,
            temperature=0,
            streaming=True
        )

        self.rewriter_llm = ChatOpenAI(
            model=final_llm_model,
            openai_api_key=final_llm_key,
            openai_api_base=llm_base_url,
            temperature=0.5
        )

        # 4. 初始化向量库
        self.index_path = os.path.abspath(os.path.join(settings.BASE_DIR, "data", "faiss_index"))
        self.vector_db = None
        if os.path.exists(os.path.join(self.index_path, "index.faiss")):
            self.vector_db = FAISS.load_local(self.index_path, self.custom_embeddings,
                                              allow_dangerous_deserialization=True)

        self.bm25_instance = None
        self.bm25_corpus = []
        self._init_bm25()

    def _init_bm25(self):
        """
        优化后的 BM25 初始化：支持多格式解析并跳过损坏文件
        """
        try:
            docs = self.db.query(KnowledgeDoc).all()
            upload_path = os.path.join(settings.BASE_DIR, "data", "uploads")
            all_texts = []

            for doc in docs:
                path = os.path.join(upload_path, doc.filename)
                if not os.path.exists(path):
                    logger.warning(f"文件不存在，跳过: {path}")
                    continue

                try:
                    ext = doc.filename.split('.')[-1].lower()
                    # 1. 动态选择加载器
                    if ext == 'pdf':
                        loader = PyPDFLoader(path)
                    elif ext == 'txt':
                        loader = TextLoader(path, encoding='utf-8')
                    elif ext == 'docx':
                        loader = Docx2txtLoader(path)
                    else:
                        logger.warning(f"未知格式，跳过: {ext}")
                        continue

                    # 2. 加载与切分
                    pages = loader.load()
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=450, chunk_overlap=100)
                    splits = text_splitter.split_documents(pages)

                    # 3. 清理文本并存入临时列表
                    for s in splits:
                        clean_t = self.strict_clean(s.page_content)
                        if len(clean_t) > 10:
                            all_texts.append(clean_t)

                except Exception as inner_e:
                    logger.error(f"处理文件 {doc.filename} 失败: {inner_e}")
                    continue

            # 4. 构建 BM25 索引
            if all_texts:
                self.bm25_corpus = all_texts
                tokenized_corpus = [list(jieba.cut(text)) for text in all_texts]
                self.bm25_instance = BM25Okapi(tokenized_corpus)
                logger.info(f"BM25 索引构建完成，共 {len(all_texts)} 条片段")
            else:
                logger.warning("BM25 没有提取到任何有效文本，索引为空")

        except Exception as e:
            logger.error(f"BM25 初始化总流程失败: {e}")

    def strict_clean(self, text: str) -> str:
        return re.sub(r'\s+', ' ', "".join(c for c in text if c.isprintable())).strip() if text else ""

    def ingest_knowledge(self, file_upload_object, filename: str) -> int:
        print(f"\n🚀 [FAISS] 开始处理文档: {filename}")

        # 1. 确保上传目录存在
        upload_path = os.path.join(settings.BASE_DIR, "data", "uploads")
        os.makedirs(upload_path, exist_ok=True)
        file_save_path = os.path.join(upload_path, filename)

        # 2. 保存文件
        with open(file_save_path, "wb") as buffer:
            shutil.copyfileobj(file_upload_object.file, buffer)

        # 3. 根据后缀选择加载器
        ext = filename.split('.')[-1].lower()
        try:
            if ext == 'pdf':
                loader = PyPDFLoader(file_save_path)
            elif ext == 'txt':
                loader = TextLoader(file_save_path, encoding='utf-8')
            elif ext == 'docx':
                loader = Docx2txtLoader(file_save_path)
            else:
                raise Exception(f"不支持的格式: {ext}")

            documents = loader.load()
        except Exception as e:
            logger.error(f"加载文件 {filename} 失败: {e}")
            raise Exception(f"文件解析失败: {str(e)}")

        # 4. 切分与清理
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=450, chunk_overlap=100,
            separators=["\n\n", "\n", "。", "；", " ", ""]
        )
        splits = text_splitter.split_documents(documents)
        valid_texts = [self.strict_clean(doc.page_content) for doc in splits if
                       len(self.strict_clean(doc.page_content)) > 10]

        if not valid_texts:
            raise Exception("文件解析后没有提取到有效文本")

        # 5. 更新索引
        if self.vector_db is None:
            self.vector_db = FAISS.from_texts(valid_texts, self.custom_embeddings)
        else:
            self.vector_db.add_texts(valid_texts)

        self.vector_db.save_local(self.index_path)
        self._init_bm25()
        return len(valid_texts)

    async def chat_stream(self, query: str, session_id: str = "default"):
        """异步流式问答生成器"""
        print(f"\n{'=' * 10} [流式请求] 用户提问: {query} {'=' * 10}")
        # 1. 预处理
        query = self.strict_clean(query)
        q_vec = self.custom_embeddings.embed_query(query)  # 提前计算向量，用于语义缓存
        history_key = f"chat_history:{session_id}"
        history_list = []
        if self.redis_client:
            raw = self.redis_client.get(history_key)
            if raw: history_list = json.loads(raw)[-16:]

        # 2. 语义缓存检查
        cached_ans, cached_src = self.cache.get_semantic_cache(q_vec)
        if cached_ans is not None:
            print(f"⚡ [命中缓存] 语义相似度匹配成功!")
            yield json.dumps({"type": "sources", "data": cached_src})
            yield json.dumps({"type": "content", "data": cached_ans})
            # 保存到历史
            if self.redis_client:
                history_list.extend([f"用户: {query}", f"助手: {cached_ans}"])
                self.redis_client.setex(history_key, 3600, json.dumps(history_list[-16:]))
            yield json.dumps({"type": "done", "full_answer": cached_ans})
            return

        if not self.vector_db:
            print("❌ 错误: 知识库未初始化")
            yield json.dumps({"type": "error", "data": "知识库为空"})
            return

        # 3. 查询改写 (Query Rewrite)
        search_query = query
        if history_list:
            history_str = "\n".join(
                [f"{'用户' if i % 2 == 0 else '助手'}: {msg}" for i, msg in enumerate(history_list[-4:])])
            rewrite_prompt = QUERY_REWRITE_PROMPT.format(history=history_str, query=query)
            try:
                rewrite_res = self.rewriter_llm.invoke(rewrite_prompt)
                search_query = rewrite_res.content.strip().replace('"', '')
                print(f"🔍 [上下文改写] 检索词变为: '{search_query}'")
            except Exception as e:
                print(f"⚠️ 查询改写失败: {e}")

        # 4. 意图分拣
        try:
            intent_res = self.rewriter_llm.invoke(INTENT_DISPATCH_PROMPT.format(query=search_query))
            match = re.search(r'\{.*\}', intent_res.content, re.DOTALL)
            if match:
                intent_obj = json.loads(match.group())
                if intent_obj.get("intent") == "NAVIGATION":
                    p = intent_obj.get("params", {})
                    print(f"🗺️ [意图识别] 命中导航: {p.get('from')} -> {p.get('to')}")
                    yield json.dumps({"type": "content", "data": f"🔄 **正在规划{p.get('mode', '驾车')}路线...**\n\n"})
                    route_info = await ToolService.get_route_plan(p.get('from'), p.get('to'), p.get('mode', 'driving'))
                    yield json.dumps({"type": "content", "data": route_info})
                    yield json.dumps({"type": "done"})
                    return
        except Exception as e:
            print(f"⚠️ 意图识别跳过: {e}")

        # 5. 混合检索与精排
        print("📡 [检索中] 正在执行混合检索...")
        faiss_docs = self.vector_db.similarity_search(search_query, k=10)
        bm25_docs = []
        if self.bm25_instance and self.bm25_corpus:
            scores = self.bm25_instance.get_scores(list(jieba.cut(search_query)))
            top_n = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:5]
            bm25_docs = [Document(page_content=self.bm25_corpus[i]) for i in top_n if scores[i] > 0]

        candidates = list(set([d.page_content for d in (faiss_docs + bm25_docs)]))
        print(f"🎯 [Rerank] 正在精排 {len(candidates)} 个候选片段...")
        try:
            ranked_indices = self.reranker.rerank(search_query, candidates)
            final_docs = [candidates[i] for i in ranked_indices[:5]]
        except:
            final_docs = candidates[:5]

        if not final_docs:
            print("❌ [检索结果] 为空")
            yield json.dumps({"type": "content", "data": "抱歉，知识库暂无相关法律条款。"})
            yield json.dumps({"type": "done"})
            return

        sources = final_docs
        yield json.dumps({"type": "sources", "data": sources})

        # 6. 图谱增强
        from app.services.graph_service import GraphService
        graph_data = GraphService(self.llm).get_full_graph(self.db)
        relevant_triples = [f"{link['source']} -{link['value']}-> {link['target']}"
                            for link in graph_data['links']
                            if any(k in link['source'] or k in link['target'] for k in jieba.cut(search_query))]
        graph_context = "\n".join(relevant_triples) if relevant_triples else "无相关逻辑关联。"

        context = "\n".join([f"[资料]: {d}" for d in final_docs])
        final_prompt = RAG_SYSTEM_PROMPT.format(context=context, history="\n".join(history_list),
                                                query=query) + f"\n\n【交通法规逻辑图谱关系链】:\n{graph_context}"

        # 7. 生成回复
        print("🤖 [AI推理] 开始生成回答...")
        full_answer = ""
        try:
            async for chunk in self.llm.astream(final_prompt):
                if chunk.content:
                    full_answer += chunk.content
                    yield json.dumps({"type": "content", "data": chunk.content}, ensure_ascii=False)

            # 8. 存入语义缓存与历史
            self.cache.set_semantic_cache(q_vec, full_answer, sources)
            if self.redis_client:
                history_list.extend([f"用户: {query}", f"助手: {full_answer}"])
                self.redis_client.setex(history_key, 3600, json.dumps(history_list[-16:]))

            print(f"✅ [流程结束] 回答生成成功\n{'-' * 60}")
            yield json.dumps({"type": "done", "full_answer": full_answer})
        except Exception as e:
            print(f"❌ [错误] 生成异常: {e}")
            yield json.dumps({"type": "error", "data": str(e)})