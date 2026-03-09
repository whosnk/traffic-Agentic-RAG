# debug_search.py
import os
from app.core.config import settings
from app.services.rag_service import AliyunEmbeddingWrapper
from langchain_community.vectorstores import FAISS
# 记得把你的 Config 配置填一下，或者确保数据库里有配置

# 1. 模拟初始化 Embedding (参数要和你项目里完全一致)
# 如果你不想手动填 Key，可以去复制 rag_service.py 里的初始化逻辑
embeddings = AliyunEmbeddingWrapper(
    model="text-embedding-v4",
    api_key="sk-72bf495af62f41bfafcbdfdf11baf500",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 2. 加载向量库
index_path = os.path.join(settings.BASE_DIR, "data", "faiss_index")
try:
    vector_db = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
    print("✅ 向量库加载成功")
except Exception as e:
    print(f"❌ 向量库加载失败: {e}")
    exit()

# 3. 暴力搜索
query = "60km/h" # 你搜不到的那个关键词
print(f"\n🔍 正在搜索: {query}")
docs = vector_db.similarity_search_with_score(query, k=5)

print("\n--- 检索结果 TOP 5 ---")
for i, (doc, score) in enumerate(docs):
    print(f"\n[{i+1}] Score: {score}")
    # 打印片段内容，看看里面是不是乱码，或者 60km/h 是不是变成了 6 0 k m / h
    print(doc.page_content[:200] + "...")