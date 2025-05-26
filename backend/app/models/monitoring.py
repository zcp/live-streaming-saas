from sqlalchemy import Column, Integer, String, DateTime, UUID, Float, ForeignKey
from sqlalchemy.sql import func
import uuid
from ..core.database import Base

class StreamQualityMetrics(Base):
    __tablename__ = "stream_quality_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stream_id = Column(UUID(as_uuid=True), nullable=False)
    bitrate = Column(Integer)
    fps = Column(Integer)
    resolution = Column(String(50))
    audio_bitrate = Column(Integer)
    audio_sample_rate = Column(Integer)
    buffer_health = Column(Float)
    error_rate = Column(Float)
    connection_count = Column(Integer)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class SystemResourceMetrics(Base):
    __tablename__ = "system_resource_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name = Column(String(50), nullable=False)
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    disk_usage = Column(Float)
    network_usage = Column(Float)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())