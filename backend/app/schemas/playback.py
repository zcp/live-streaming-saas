from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from .models import PlaybackStatus, PlaybackPermissionType

# PlaybackRecord schemas
class PlaybackRecordBase(BaseModel):
    stream_id: UUID
    user_id: int
    title: str
    description: Optional[str] = None
    video_path: str
    duration: Optional[int] = None
    file_size: Optional[int] = None
    resolution: Optional[str] = None
    format: Optional[str] = None
    storage_type: Optional[str] = None
    region: str
    provider: str
    is_public: bool = True
    permission_level: int = 0

class PlaybackRecordCreate(PlaybackRecordBase):
    pass

class PlaybackRecordUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    permission_level: Optional[int] = None
    status: Optional[PlaybackStatus] = None

class PlaybackRecordInDB(PlaybackRecordBase):
    id: UUID
    status: PlaybackStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# PlaybackSegment schemas
class PlaybackSegmentBase(BaseModel):
    segment_path: str
    segment_index: int
    duration: int
    file_size: int
    quality_metrics: Optional[Dict[str, Any]] = None

class PlaybackSegmentCreate(PlaybackSegmentBase):
    playback_id: UUID

class PlaybackSegmentUpdate(BaseModel):
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    quality_metrics: Optional[Dict[str, Any]] = None

class PlaybackSegmentInDB(PlaybackSegmentBase):
    id: UUID
    playback_id: UUID
    start_time: datetime
    end_time: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# PlaybackQuality schemas
class PlaybackQualityBase(BaseModel):
    bitrate: Optional[int] = None
    fps: Optional[int] = None
    audio_bitrate: Optional[int] = None
    audio_sample_rate: Optional[int] = None

class PlaybackQualityCreate(PlaybackQualityBase):
    playback_id: UUID

class PlaybackQualityUpdate(PlaybackQualityBase):
    pass

class PlaybackQualityInDB(PlaybackQualityBase):
    id: UUID
    playback_id: UUID
    created_at: datetime

    class Config:
        orm_mode = True

# PlaybackStats schemas
class PlaybackStatsBase(BaseModel):
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0

class PlaybackStatsCreate(PlaybackStatsBase):
    playback_id: UUID

class PlaybackStatsUpdate(PlaybackStatsBase):
    pass

class PlaybackStatsInDB(PlaybackStatsBase):
    id: UUID
    playback_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# PlaybackPermission schemas
class PlaybackPermissionBase(BaseModel):
    user_id: int
    playback_id: UUID
    permission_type: PlaybackPermissionType
    is_public: bool = False

class PlaybackPermissionCreate(PlaybackPermissionBase):
    pass

class PlaybackPermissionUpdate(BaseModel):
    permission_type: Optional[PlaybackPermissionType] = None
    is_public: Optional[bool] = None

class PlaybackPermissionInDB(PlaybackPermissionBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# PlaybackPermissionRule schemas
class PlaybackPermissionRuleBase(BaseModel):
    rule_type: str
    rule_value: str
    permission_type: PlaybackPermissionType

class PlaybackPermissionRuleCreate(PlaybackPermissionRuleBase):
    pass

class PlaybackPermissionRuleUpdate(BaseModel):
    rule_type: Optional[str] = None
    rule_value: Optional[str] = None
    permission_type: Optional[PlaybackPermissionType] = None

class PlaybackPermissionRuleInDB(PlaybackPermissionRuleBase):
    id: UUID
    created_at: datetime

    class Config:
        orm_mode = True

# 响应模型
class PlaybackRecordWithDetails(PlaybackRecordInDB):
    segments: List[PlaybackSegmentInDB] = []
    quality: Optional[PlaybackQualityInDB] = None
    stats: Optional[PlaybackStatsInDB] = None
    permissions: List[PlaybackPermissionInDB] = []