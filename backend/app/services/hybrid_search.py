# app/services/hybrid_search.py
import jieba
from rank_bm25 import BM25Okapi

class HybridSearcher:
    def __init__(self, documents):
        # 对所有文档进行分词
        self.tokenized_docs = [list(jieba.cut(doc)) for doc in documents]
        self.bm25 = BM25Okapi(self.tokenized_docs)
        self.documents = documents

    def search(self, query: str, top_k: int = 5):
        # 对查询进行分词
        tokenized_query = list(jieba.cut(query))
        # 获取 BM25 分数
        scores = self.bm25.get_scores(tokenized_query)
        # 获取 Top-K 索引
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [self.documents[i] for i in top_indices]