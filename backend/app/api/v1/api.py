from fastapi import APIRouter
from app.api.v1.endpoints import stream

api_router = APIRouter()
api_router.include_router(stream.router, prefix="/streams", tags=["streams"])

# 导出 api_router
__all__ = ["api_router"]