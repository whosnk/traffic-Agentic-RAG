# app/api/endpoints/test.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from pydantic import BaseModel

router = APIRouter()


# --- 依赖注入 (Dependency Injection) ---
# 这是一个非常经典的设计模式，确保每个请求都有独立的数据库会话，
# 请求结束自动关闭，防止数据库连接泄露。
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 定义请求体结构 (Pydantic Schema)
class UserCreateSchema(BaseModel):
    username: str
    password: str


@router.get("/health")
def health_check():
    return {"status": "ok", "message": "后端服务运行正常 🚀"}


@router.post("/users/")
def create_user(user: UserCreateSchema, db: Session = Depends(get_db)):
    # 1. 查重
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 2. 创建
    new_user = User(username=user.username, password=user.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "username": new_user.username}