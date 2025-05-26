# app/schemas/storage.py
from pydantic import BaseModel, UUID4, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

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

# 存储类型基础模型
class StorageTypeBase(BaseModel):
    name: str
    description: Optional[str] = None

class StorageTypeCreate(StorageTypeBase):
    pass

class StorageTypeUpdate(StorageTypeBase):
    name: Optional[str] = None

class StorageType(StorageTypeBase):
    id: UUID4
    created_at: datetime

    class Config:
        from_attributes = True

# 存储配置基础模型
class StorageConfigBase(BaseModel):
    provider: StorageProvider
    region: Region
    environment: str = Field(..., min_length=1, max_length=20)
    version: int = Field(..., gt=0)
    config_data: Dict[str, Any]
    is_active: bool = True

# 创建存储配置请求模型
class StorageConfigCreate(StorageConfigBase):
    storage_type_id: UUID4

# 更新存储配置请求模型
class StorageConfigUpdate(BaseModel):
    provider: Optional[StorageProvider] = None
    region: Optional[Region] = None
    environment: Optional[str] = Field(None, min_length=1, max_length=20)
    version: Optional[int] = Field(None, gt=0)
    config_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    storage_type_id: Optional[UUID4] = None

# 存储配置响应模型
class StorageConfig(StorageConfigBase):
    id: UUID4
    storage_type_id: UUID4
    storage_type: StorageType  # 添加与 StorageType 的关系
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# 存储类型响应模型（包含配置列表）
class StorageTypeWithConfigs(StorageType):
    configs: List[StorageConfig] = []  # 添加与 StorageConfig 的关系



