
# app/models/storage.py
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, UUID, Boolean, ForeignKey, JSON,Text
from sqlalchemy.sql import func
import uuid
from ..core.database import Base
from sqlalchemy.orm import relationship


class StorageProvider(str, Enum):
    AWS = "aws"
    ALIYUN = "aliyun"
    AZURE = "azure"
    LOCAL = "local"

class Region(str, Enum):
    # AWS regions
    US_EAST_1 = "us-east-1"
    US_WEST_1 = "us-west-1"
    # 阿里云 regions
    CN_HANGZHOU = "cn-hangzhou"
    CN_SHANGHAI = "cn-shanghai"

class StorageType(Base):
    __tablename__ = "storage_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    configs = relationship("StorageConfig", back_populates="storage_type")


class StorageConfig(Base):
    __tablename__ = "storage_configs"
    # ... 其他字段保持不变 ...
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # 添加主键
    storage_type_id = Column(UUID(as_uuid=True), ForeignKey("storage_types.id"))
    provider = Column(String(20), nullable=False)
    region = Column(String(50), nullable=False)

    # 添加关系
    storage_type = relationship("StorageType", back_populates="configs")