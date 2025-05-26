from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, UUID, ForeignKey, BigInteger, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from enum import Enum
from ..core.database import Base

class PlaybackStatus(str, Enum):
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    DELETED = "deleted"

class PlaybackPermissionType(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    MANAGE = "manage"

class PlaybackRecord(Base):
    __tablename__ = "playback_record"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stream_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(Integer, nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    video_path = Column(String(255), nullable=False)
    duration = Column(Integer)
    file_size = Column(BigInteger)
    resolution = Column(String(50))
    format = Column(String(20))
    storage_type = Column(String(20))
    status = Column(String(20), default=PlaybackStatus.PROCESSING)
    region = Column(String(50), nullable=False)
    provider = Column(String(20), nullable=False)
    is_public = Column(Boolean, default=True)
    permission_level = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    segments = relationship("PlaybackSegment", back_populates="playback")
    quality = relationship("PlaybackQuality", back_populates="playback")
    stats = relationship("PlaybackStats", back_populates="playback")
    permissions = relationship("PlaybackPermission", back_populates="playback")

class PlaybackSegment(Base):
    __tablename__ = "playback_segments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playback_id = Column(UUID(as_uuid=True), ForeignKey("playback_record.id"))
    segment_path = Column(String(255), nullable=False)
    segment_index = Column(Integer, nullable=False)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Integer, default=0)  # 单位：秒
    file_size = Column(BigInteger, nullable=False)
    quality_metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    playback = relationship("PlaybackRecord", back_populates="segments")

class PlaybackQuality(Base):
    __tablename__ = "playback_quality"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playback_id = Column(UUID(as_uuid=True), ForeignKey("playback_record.id"))
    bitrate = Column(Integer)
    fps = Column(Integer)
    audio_bitrate = Column(Integer)
    audio_sample_rate = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    playback = relationship("PlaybackRecord", back_populates="quality")

class PlaybackStats(Base):
    __tablename__ = "playback_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playback_id = Column(UUID(as_uuid=True), ForeignKey("playback_record.id"))
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    playback = relationship("PlaybackRecord", back_populates="stats")


class PlaybackPermission(Base):
    __tablename__ = "playback_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, nullable=False)
    playback_id = Column(UUID(as_uuid=True), ForeignKey("playback_record.id"), nullable=False)  # 添加回放记录ID
    permission_type = Column(String(20), nullable=False, default=PlaybackPermissionType.READ)  # 使用枚举类型
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 添加关系
    playback = relationship("PlaybackRecord", back_populates="permissions")

class PlaybackPermissionRule(Base):
    __tablename__ = "playback_permission_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_type = Column(String(50), nullable=False)
    rule_value = Column(JSON, nullable=False)
    permission_type = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


