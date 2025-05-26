# app/api/v1/endpoints/stream.py
import os
import shutil
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.services.stream import StreamService
from app.schemas.stream import (
    StreamCreate, StreamUpdate, Stream, StreamList,
    StreamStatusUpdate, StreamSearch, StreamPermissionCreate,
    StreamPermissionUpdate, StreamPermission, StreamPermissionRuleCreate,
    StreamPermissionRuleUpdate, StreamPermissionRule
)

from app.core.config import settings

router = APIRouter()


@router.get("/")
async def list_streams(
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user)
):
    try:
        print(f"获取用户 {current_user['id']} 的直播流列表")  # 添加日志
        service = StreamService(db)
        streams = service.get_user_streams(current_user["id"])
        print(f"找到 {len(streams)} 个直播流")  # 添加日志

        return {
            "message": "success",
            "data": [
                {
                    "id": str(stream.id),
                    "title": stream.title,
                    "description": stream.description,
                    "cover_url": stream.cover_url,
                    "stream_key": stream.stream_key,
                    "storage_type": stream.storage_type,
                    "status": stream.status,
                    "region": stream.region,
                    "provider": stream.provider,
                    "is_private": stream.is_private,
                    "is_recorded": stream.is_recorded,
                    "created_at": stream.created_at
                }
                for stream in streams
            ]
        }
    except Exception as e:
        print(f"获取直播流列表失败: {str(e)}")  # 添加日志
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_stream(
    stream: StreamCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """创建直播流"""
    try:
        print("1")
        service = StreamService(db)
        print("2")
        db_stream = service.create_stream(stream, current_user["id"])
        print("3")
        return {
            "message": "success",
            "data": {
                "stream_id": str(db_stream.id),
                "stream_key": db_stream.stream_key,
                "status": db_stream.status
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{stream_id}", response_model=Stream)
def get_stream(
    stream_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = StreamService(db)
    stream = service.get_stream(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return stream

@router.get("/", response_model=StreamList)
def search_streams(
    search: StreamSearch = Depends(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = StreamService(db)
    streams, total = service.search_streams(search)
    return StreamList(total=total, items=streams)

@router.put("/{stream_id}", response_model=Stream)
def update_stream(
    stream_id: UUID,
    stream: StreamUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = StreamService(db)
    db_stream = service.get_stream(stream_id)
    if not db_stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    if db_stream.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return service.update_stream(stream_id, stream)

@router.delete("/{stream_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stream(
    stream_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = StreamService(db)
    db_stream = service.get_stream(stream_id)
    if not db_stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    if db_stream.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    if not service.delete_stream(stream_id):
        raise HTTPException(status_code=400, detail="Failed to delete stream")

@router.put("/{stream_id}/status", response_model=Stream)
def update_stream_status(
    stream_id: UUID,
    status_update: StreamStatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = StreamService(db)
    db_stream = service.get_stream(stream_id)
    if not db_stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    if db_stream.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return service.update_stream_status(stream_id, status_update)

@router.post("/{stream_id}/permissions", response_model=StreamPermission)
def create_stream_permission(
    stream_id: UUID,
    permission: StreamPermissionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = StreamService(db)
    db_stream = service.get_stream(stream_id)
    if not db_stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    if db_stream.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return service.create_stream_permission(permission)

@router.put("/permissions/{permission_id}", response_model=StreamPermission)
def update_stream_permission(
    permission_id: UUID,
    permission: StreamPermissionUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = StreamService(db)
    return service.update_stream_permission(permission_id, permission)

@router.post("/permission-rules", response_model=StreamPermissionRule)
def create_stream_permission_rule(
    rule: StreamPermissionRuleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = StreamService(db)
    return service.create_stream_permission_rule(rule)

@router.put("/permission-rules/{rule_id}", response_model=StreamPermissionRule)
def update_stream_permission_rule(
    rule_id: UUID,
    rule: StreamPermissionRuleUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = StreamService(db)
    return service.update_stream_permission_rule(rule_id, rule)


@router.post("/{stream_id}/push")
async def start_streaming(
    stream_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """启动推流"""
    try:
        print("开始推流")
        service = StreamService(db)
        success = await service.start_streaming(stream_id)
        if not success:
            raise HTTPException(status_code=400, detail="启动推流失败")
        else:
           print("success is true")

        return {"message": "success", "data": {"status": "streaming"}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{stream_id}/stop")
async def stop_streaming(
    stream_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """停止推流"""
    try:
        service = StreamService(db)
        success = await service.stop_streaming(stream_id)
        if not success:
            raise HTTPException(status_code=400, detail="停止推流失败")
        return {"message": "success", "data": {"status": "ended"}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{stream_id}/upload")
async def upload_video(
    stream_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """上传视频文件"""
    try:
        # 获取直播流信息
        service = StreamService(db)
        stream = service.get_stream(stream_id)
        if not stream:
            raise HTTPException(status_code=404, detail="直播流不存在")

        # 创建上传目录
        upload_dir = os.path.join(settings.UPLOAD_DIR, str(stream_id))
        os.makedirs(upload_dir, exist_ok=True)

        # 保存文件
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 更新直播流信息
        success = await service.upload_video(stream_id, file_path)
        if not success:
            raise HTTPException(status_code=400, detail="上传视频失败")

        return {
            "message": "success",
            "data": {
                "file_path": file_path,
                "status": stream.status
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))