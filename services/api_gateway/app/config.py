from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "StreamForge"
    SECRET_KEY: str
    ALGORITHM: str
    RABBITMQ_HOST: str
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    # Optional: when set, the rate limiter uses Redis for shared state across
    # replicas. When unset, the limiter falls back to in-memory (single-process).
    REDIS_URL: Optional[str] = None
    POSTGRES_URL: str
    BUCKET_NAME: str
    model_config = SettingsConfigDict(env_file=".env")
    VIDEO_QUEUE: str
    DLQ_QUEUE: str
    VIDEO_DLX: str
    VIDEO_FAILED_ROUTING_KEY: str


settings = Settings()
