# app/schemas/user.py
from pydantic import BaseModel
from typing import Optional

# 注册/登录时接收的字段
class UserAuth(BaseModel):
    username: str
    password: str

# 返回给前端的用户信息（隐藏密码）
class UserOut(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        from_attributes = True

# Token 返回格式
class Token(BaseModel):
    access_token: str
    token_type: str