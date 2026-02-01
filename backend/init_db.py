from app.db.session import engine
from app.db.base import Base
# 导入 models 包，会触发 __init__.py 里的所有导入
import app.models

def init_db():
    print("正在初始化数据库表结构...")
    # 此时 Base.metadata 已经包含了 User 和 AIConfig
    Base.metadata.create_all(bind=engine)
    print("数据库表初始化完成！")

if __name__ == "__main__":
    init_db()