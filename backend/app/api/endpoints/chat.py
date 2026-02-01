import json
import logging
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import ChatSession, ChatMessage, User
from app.services.rag_service import RAGService
from app.core.security import SECRET_KEY, ALGORITHM
from pydantic import BaseModel

# 配置
reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
router = APIRouter()
logger = logging.getLogger(__name__)


# --- 数据库依赖 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- 身份验证依赖 ---
def get_current_user(db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="无效的 Token")
    except Exception:
        raise HTTPException(status_code=401, detail="登录已过期或凭证无效")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


# --- 请求模型 ---
class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = "default"


# --- RAG 服务注入 ---
def get_rag_service(db: Session = Depends(get_db)):
    return RAGService(db)


# --- 1. 问答接口 (增加用户隔离) ---
@router.post("/ask")
async def ask_question(
        request: ChatRequest,
        db: Session = Depends(get_db),
        service: RAGService = Depends(get_rag_service),
        current_user: User = Depends(get_current_user)
):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")

    try:
        session = db.query(ChatSession).filter(ChatSession.id == request.session_id).first()
        if not session:
            title = request.question[:15] + "..." if len(request.question) > 15 else request.question
            session = ChatSession(id=request.session_id, title=title, user_id=current_user.id)
            db.add(session)
        else:
            if session.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="无权操作此会话")

        # 保存用户消息
        user_msg = ChatMessage(session_id=request.session_id, role="user", content=request.question)
        db.add(user_msg)

        # 获取 AI 回答
        answer, sources = service.chat(request.question, request.session_id)

        # 保存 AI 消息
        ai_msg = ChatMessage(
            session_id=request.session_id,
            role="ai",
            content=answer,
            sources=json.dumps(sources)
        )
        db.add(ai_msg)

        # 强制触发 updated_at 更新，让会话在侧边栏置顶
        from datetime import datetime
        session.updated_at = datetime.now()

        db.commit()
        return {"status": "success", "answer": answer, "sources": sources}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# --- 2. 获取会话列表 (仅限当前用户) ---
@router.get("/sessions")
def list_sessions(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 只返回当前用户的会话列表
    return db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.updated_at.desc()).all()


# --- 3. 获取历史消息 (增加权限校验) ---
@router.get("/history/{session_id}")
def get_history(
        session_id: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 先检查会话是否存在且属于该用户
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或无访问权限")

    return db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.asc()).all()


# --- 4. 知识库上传 (可选：仅限管理员) ---
@router.post("/upload")
async def upload_knowledge_file(
    file: UploadFile = File(...),
    service: RAGService = Depends(get_rag_service),
    current_user: User = Depends(get_current_user)
):
    # 可以在这里增加：if current_user.role != "admin": raise HTTPException(403)
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持PDF格式")
    try:
        count = service.ingest_pdf(file, file.filename)
        return {"status": "success", "message": f"解析完成，存入{count}条知识块"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "avatar": current_user.avatar,
        "role": current_user.role,
        "created_at": current_user.created_at.strftime("%Y-%m-%d") if current_user.created_at else "2025-01-01"
    }


@router.post("/upload_avatar")
async def upload_avatar(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1. 校验后缀
    ext = file.filename.split(".")[-1]
    if ext.lower() not in ["png", "jpg", "jpeg"]:
        raise HTTPException(400, "仅支持 png/jpg")

    # 2. 保存文件
    filename = f"user_{current_user.id}.{ext}"
    save_path = f"data/uploads/avatars/{filename}"
    with open(save_path, "wb") as f:
        f.write(await file.read())

    # 3. 更新数据库 (返回相对路径)
    avatar_url = f"/static/avatars/{filename}"
    current_user.avatar = avatar_url
    db.commit()
    return {"avatar_url": avatar_url}