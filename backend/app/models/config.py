from sqlalchemy import Column, Integer, String, Boolean
from app.db.base import Base

class AIConfig(Base):
    __tablename__ = "ai_configs"

    id = Column(Integer, primary_key=True, index=True)
    config_type = Column(String(20))  # 'llm' 或 'embedding'
    provider_name = Column(String(50)) # 例如 'Aliyun', 'DeepSeek'
    base_url = Column(String(255))
    api_key = Column(String(255))
    model_name = Column(String(100))
    is_active = Column(Boolean, default=False) # 是否正在使用