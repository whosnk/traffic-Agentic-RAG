# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings # 引入刚才写的配置

engine_kwargs = {"pool_pre_ping": True}
if settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.SQLALCHEMY_DATABASE_URI, **engine_kwargs)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
