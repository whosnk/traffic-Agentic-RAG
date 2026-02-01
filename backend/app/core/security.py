# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional, Union, Any
from jose import jwt
from passlib.context import CryptContext

# 1. 设置密码加密算法（bcrypt 是目前最安全的算法之一）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 2. JWT 配置（通常建议放在 config.py，这里为了演示直观先放这）
SECRET_KEY = "suibian_zhao_yige_chang_de_zi_fu_chuan"  # 签名密钥，决不能泄露
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # Token 有效期（1天）


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码和哈希密码是否匹配"""
    return pwd_context.verify(plain_password[:72], hashed_password)


def get_password_hash(password: str) -> str:
    """对明文密码进行哈希加密"""
    # 额外保险：如果用户输入的密码由于某种原因极其长（超过72位），截断它
    # bcrypt 算法本身不支持超过72位的明文
    return pwd_context.hash(password[:72])


def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """生成 JWT Token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # 负载数据：通常存入用户的 ID 或 用户名
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt