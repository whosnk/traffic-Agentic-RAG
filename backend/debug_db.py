# debug_db.py
import os
import shutil
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

# 模拟一个极简的 Embedding 类
class SimpleEmb:
    def embed_documents(self, texts): return [[0.1] * 1536] * len(texts)
    def embed_query(self, text): return [0.1] * 1536

path = "./test_db"
if os.path.exists(path): shutil.rmtree(path)

print("正在尝试初始化本地数据库...")
try:
    db = Chroma(
        collection_name="test",
        persist_directory=path,
        embedding_function=SimpleEmb()
    )
    print("写入测试数据...")
    db.add_texts(texts=["hello world", "test traffic"])
    print("数据库写入成功！文件夹已生成在:", os.path.abspath(path))
except Exception as e:
    print("数据库操作失败:", str(e))