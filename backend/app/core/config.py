import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # 1. 先定义项目根目录 (设为类属性)
    # resolve().parent.parent.parent 对应: backend/app/core -> backend/app -> backend -> 根目录
    BASE_DIR: str = str(Path(__file__).resolve().parent.parent.parent)

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "交通治理决策智能体"

    # --- 数据库配置 ---
    SQLITE_URL: str = ""
    MYSQL_USER: str = ""
    MYSQL_PASSWORD: str = ""
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_DB: str = ""

    # --- AI 配置 (作为可选，因为我们现在改用数据库存了) ---
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None

    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379

    # --- 增加高德 Key ---
    AMAP_KEY: Optional[str] = None

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        if self.SQLITE_URL:
            return self.SQLITE_URL
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
        )

    # 2. 动态获取 .env 路径
    model_config = SettingsConfigDict(
        # 这里直接用 Path 计算，不依赖 self
        env_file=os.path.join(str(Path(__file__).resolve().parent.parent.parent), ".env"),
        case_sensitive=True,
        extra='ignore'
    )


settings = Settings()
