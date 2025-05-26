# app/schemas/stream.py
from uuid import UUID

from pydantic import BaseModel, UUID4, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class StreamStatus(str, Enum):
    CREATED = "created"
    SCHEDULED = "scheduled"
    STREAMING = "streaming"
    PAUSED = "paused"
    ENDED = "ended"
    ERROR = "error"

class StreamPermissionType(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    MANAGE = "manage"

# 基础模型
class StreamBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    cover_url: Optional[str] = None
    is_private: bool = False
    is_recorded: bool = True
    category_id: Optional[UUID] = None
    sub_category_id: Optional[int] = None
    thumbnail_url: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    permission_level: int = 0

# 创建直播请求模型
class StreamCreate(StreamBase):
    region: str
    provider: str
    storage_type: str

# 更新直播请求模型
class StreamUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    cover_url: Optional[str] = None
    is_private: Optional[bool] = None
    is_recorded: Optional[bool] = None
    category_id: Optional[UUID] = None
    sub_category_id: Optional[int] = None
    thumbnail_url: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    permission_level: Optional[int] = None
    status: Optional[StreamStatus] = None
    is_streaming: Optional[bool] = None  # 添加这个字段
    stream_error: Optional[str] = None  # 添加这个字段
    stream_health: Optional[str] = None  # 添加这个字段
    max_concurrent_viewers: Optional[int] = None  # 添加这个字段
    total_viewers: Optional[int] = None  # 添加这个字段

# 权限规则值模型
class RuleValue(BaseModel):
    conditions: List[dict]
    combine_type: str = "and"  # or "or"

# 权限规则模型
class StreamPermissionRuleBase(BaseModel):
    rule_type: str
    rule_value: RuleValue
    permission_type: StreamPermissionType

class StreamPermissionRuleCreate(StreamPermissionRuleBase):
    pass

class StreamPermissionRuleUpdate(BaseModel):
    rule_type: Optional[str] = None
    rule_value: Optional[RuleValue] = None
    permission_type: Optional[StreamPermissionType] = None

class StreamPermissionRule(StreamPermissionRuleBase):
    id: UUID4
    created_at: datetime

    class Config:
        from_attributes = True

# 权限模型
class StreamPermissionBase(BaseModel):
    user_id: int
    permission_type: StreamPermissionType
    is_public: bool = False

class StreamPermissionCreate(StreamPermissionBase):
    stream_id: UUID4

class StreamPermissionUpdate(BaseModel):
    permission_type: Optional[StreamPermissionType] = None
    is_public: Optional[bool] = None

class StreamPermission(StreamPermissionBase):
    id: UUID4
    stream_id: UUID4
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# 直播响应模型
class Stream(StreamBase):
    id: UUID4
    user_id: int
    stream_key: str
    storage_type: str
    stream_path: Optional[str]
    storage_bucket: Optional[str]
    status: StreamStatus
    region: str
    provider: str
    is_streaming: bool = False  # 添加这个字段
    stream_error: Optional[str] = None  # 添加这个字段
    stream_health: str = "good"  # 添加这个字段
    max_concurrent_viewers: int = 0  # 添加这个字段
    total_viewers: int = 0  # 添加这个字段
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    permissions: List[StreamPermission] = []
    permission_rules: List[StreamPermissionRule] = []

    class Config:
        from_attributes = True

# 直播列表响应模型
class StreamList(BaseModel):
    total: int
    items: List[Stream]

# 直播状态更新模型
class StreamStatusUpdate(BaseModel):
    status: StreamStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

# 直播搜索模型
class StreamSearch(BaseModel):
    title: Optional[str] = None
    status: Optional[StreamStatus] = None
    category_id: Optional[int] = None
    is_private: Optional[bool] = None
    start_time_from: Optional[datetime] = None
    start_time_to: Optional[datetime] = None
    page: int = 1
    page_size: int = 20