from app.db.session import SessionLocal
from app.models.config import AIConfig
from app.db.base import Base
from app.db.session import engine


def setup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 1. 插入阿里云 Embedding 配置
    aliyun_emb = AIConfig(
        config_type="embedding",
        provider_name="Aliyun",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="sk-72bf495af62f41bfafcbdfdf11baf500",  # 你刚才提供的
        model_name="text-embedding-v4",
        is_active=True
    )

    # 2. 插入 DeepSeek LLM 配置
    deepseek_llm = AIConfig(
        config_type="llm",
        provider_name="DeepSeek",
        base_url="https://api.deepseek.com",
        api_key="sk-7398655341054eda8e7877524e971428",
        model_name="deepseek-chat",
        is_active=True
    )

    db.add(aliyun_emb)
    db.add(deepseek_llm)
    db.commit()
    print("AI 配置初始化成功！")


if __name__ == "__main__":
    setup()