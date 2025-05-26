# backend/app/core/config.py
from pydantic_settings import BaseSettings

SRS_SERVER = {
    "host": "124.220.235.226",
    "port": 1935,
    "app": "live"
}

FFMPEG_CONFIG = {
    "video_bitrate": "2500k",
    "audio_bitrate": "128k",
    "preset": "veryfast"
}
class Settings(BaseSettings):
    PROJECT_NAME: str = "Live Streaming API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # 数据库配置
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "324zq999"
    POSTGRES_DB: str = "livestream_saas"
    DATABASE_URL: str = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}/{POSTGRES_DB}"
    SQLALCHEMY_DATABASE_URI: str = DATABASE_URL  # 为了兼容性保留
    class Config:
        case_sensitive = True




settings = Settings()