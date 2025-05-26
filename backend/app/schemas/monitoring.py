# app/schemas/monitoring.py
from pydantic import BaseModel, UUID4, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ServiceName(str, Enum):
    STREAM = "stream"
    PLAYBACK = "playback"
    STORAGE = "storage"
    MONITORING = "monitoring"

# 流质量指标基础模型
class StreamQualityMetricsBase(BaseModel):
    stream_id: UUID4
    bitrate: Optional[int] = None
    fps: Optional[int] = None
    resolution: Optional[str] = None
    audio_bitrate: Optional[int] = None
    audio_sample_rate: Optional[int] = None
    buffer_health: Optional[float] = Field(None, ge=0.0, le=1.0)
    error_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    connection_count: Optional[int] = Field(None, ge=0)

# 创建流质量指标请求模型
class StreamQualityMetricsCreate(StreamQualityMetricsBase):
    pass

# 流质量指标响应模型
class StreamQualityMetrics(StreamQualityMetricsBase):
    id: UUID4
    timestamp: datetime

    class Config:
        from_attributes = True

# 流质量指标列表响应模型
class StreamQualityMetricsList(BaseModel):
    total: int
    items: List[StreamQualityMetrics]

# 流质量指标搜索模型
class StreamQualityMetricsSearch(BaseModel):
    stream_id: Optional[UUID4] = None
    timestamp_from: Optional[datetime] = None
    timestamp_to: Optional[datetime] = None
    min_bitrate: Optional[int] = None
    max_bitrate: Optional[int] = None
    min_fps: Optional[int] = None
    max_fps: Optional[int] = None
    min_buffer_health: Optional[float] = None
    max_buffer_health: Optional[float] = None
    min_error_rate: Optional[float] = None
    max_error_rate: Optional[float] = None
    page: int = 1
    page_size: int = 20

# 系统资源指标基础模型
class SystemResourceMetricsBase(BaseModel):
    service_name: ServiceName
    cpu_usage: Optional[float] = Field(None, ge=0.0, le=100.0)
    memory_usage: Optional[float] = Field(None, ge=0.0, le=100.0)
    disk_usage: Optional[float] = Field(None, ge=0.0, le=100.0)
    network_usage: Optional[float] = Field(None, ge=0.0)

# 创建系统资源指标请求模型
class SystemResourceMetricsCreate(SystemResourceMetricsBase):
    pass

# 系统资源指标响应模型
class SystemResourceMetrics(SystemResourceMetricsBase):
    id: UUID4
    timestamp: datetime

    class Config:
        from_attributes = True

# 系统资源指标列表响应模型
class SystemResourceMetricsList(BaseModel):
    total: int
    items: List[SystemResourceMetrics]

# 系统资源指标搜索模型
class SystemResourceMetricsSearch(BaseModel):
    service_name: Optional[ServiceName] = None
    timestamp_from: Optional[datetime] = None
    timestamp_to: Optional[datetime] = None
    min_cpu_usage: Optional[float] = None
    max_cpu_usage: Optional[float] = None
    min_memory_usage: Optional[float] = None
    max_memory_usage: Optional[float] = None
    min_disk_usage: Optional[float] = None
    max_disk_usage: Optional[float] = None
    min_network_usage: Optional[float] = None
    max_network_usage: Optional[float] = None
    page: int = 1
    page_size: int = 20

# 监控指标聚合模型
class MetricsAggregation(BaseModel):
    service_name: ServiceName
    metric_type: str
    aggregation_type: str  # avg, max, min, sum
    value: float
    timestamp: datetime

# 监控告警模型
class MonitoringAlert(BaseModel):
    service_name: ServiceName
    metric_type: str
    threshold: float
    current_value: float
    severity: str  # info, warning, error, critical
    message: str
    timestamp: datetime

# 监控指标统计模型
class MetricsStatistics(BaseModel):
    service_name: ServiceName
    metric_type: str
    avg_value: float
    max_value: float
    min_value: float
    total_count: int
    timestamp_from: datetime
    timestamp_to: datetime