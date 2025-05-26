# app/models/stream.py

from sqlalchemy import Column, Integer, String, DateTime, Boolean, UUID, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
import uuid
from enum import Enum

from ..core.database import Base

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

class StreamCategory(Base):
    __tablename__ = "stream_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False)
    parent_id = Column(Integer)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 修改关系定义，使用 primaryjoin 明确指定连接条件
    # 修改关系定义
    streams = relationship(
        "LiveStream",
        back_populates="category",
        primaryjoin="StreamCategory.id == LiveStream.category_id"
    )

class StreamTag(Base):
    __tablename__ = "stream_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    streams = relationship("LiveStream", secondary="stream_tag_relations", back_populates="tags")

class StreamTagRelation(Base):
    __tablename__ = "stream_tag_relations"

    stream_id = Column(UUID(as_uuid=True), ForeignKey("live_stream.id"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("stream_tags.id"), primary_key=True)


class StreamStatistics(Base):
    __tablename__ = "stream_statistics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stream_id = Column(UUID(as_uuid=True), ForeignKey("live_stream.id"))
    total_viewer_count = Column(Integer, default=0)
    peak_viewer_count = Column(Integer, default=0)
    total_like_count = Column(Integer, default=0)
    total_share_count = Column(Integer, default=0)
    total_comment_count = Column(Integer, default=0)
    last_view_time = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    stream = relationship("LiveStream", back_populates="statistics")

class LiveStream(Base):
    __tablename__ = "live_stream"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    cover_url = Column(String(255))
    scheduled_time = Column(DateTime)
    permission_level = Column(Integer, default=0)
    is_private = Column(Boolean, default=False)
    is_recorded = Column(Boolean, default=True)
    category_id = Column(Integer)
    sub_category_id = Column(Integer)
    thumbnail_url = Column(String(255))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    stream_key = Column(String(255), nullable=False)
    storage_type = Column(String(20), nullable=False)
    stream_path = Column(String(255))
    storage_bucket = Column(String(100))
    region = Column(String(50), nullable=False)
    provider = Column(String(20), nullable=False)

    status = Column(String(20), default=StreamStatus.CREATED)
    is_streaming = Column(Boolean, default=False)
    stream_error = Column(String(255))
    stream_health = Column(String(20), default="good")

    start_time = Column(DateTime)
    end_time = Column(DateTime)
    max_concurrent_viewers = Column(Integer, default=0)  # 本次推流最大并发观众数
    total_viewers = Column(Integer, default=0)    # 本次推流总观众数

    # 关系
    category_id = Column(UUID(as_uuid=True), ForeignKey("stream_categories.id"))

    # 修改关系定义，添加 primaryjoin
    category = relationship(
        "StreamCategory",
        back_populates="streams",
        primaryjoin="LiveStream.category_id == StreamCategory.id"
    )
    statistics = relationship("StreamStatistics", back_populates="stream")
    tags = relationship("StreamTag", secondary="stream_tag_relations", back_populates="streams")
    permissions = relationship("StreamPermission", back_populates="stream")

class StreamPermission(Base):
    __tablename__ = "stream_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stream_id = Column(UUID(as_uuid=True), ForeignKey("live_stream.id"))
    user_id = Column(Integer, nullable=False)
    permission_type = Column(String(20), nullable=False)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    stream = relationship("LiveStream", back_populates="permissions")

class StreamPermissionRule(Base):
    __tablename__ = "stream_permission_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_type = Column(String(50), nullable=False)
    rule_value = Column(JSON, nullable=False)
    permission_type = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

