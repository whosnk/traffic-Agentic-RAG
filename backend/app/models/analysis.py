from sqlalchemy import Column, Integer, String, DateTime, JSON
from app.db.base import Base
from datetime import datetime

class HotTopic(Base):
    __tablename__ = "hot_topics"
    id = Column(Integer, primary_key=True, index=True)
    topic_name = Column(String(255))   # AI 总结的主题名，如“酒驾处罚标准”
    keywords = Column(JSON)            # 关键词列表，如 ["罚款", "拘留", "营运车"]
    hit_count = Column(Integer)        # 这一堆里有多少个问题
    representative_queries = Column(JSON) # 代表性的 3 个原始问题
    created_at = Column(DateTime, default=datetime.now)