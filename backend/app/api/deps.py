# backend/app/api/deps.py
from typing import Generator
from sqlalchemy.orm import Session
from app.db.session import SessionLocal

def get_db() -> Generator:
    """
    获取数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user():
    """
    获取当前用户
    """
    # TODO: 实现用户认证
    return {"id": 1}  # 临时返回测试用户