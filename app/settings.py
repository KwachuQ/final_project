from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    DATABASE_URL: str
    SECRET_KEY: str
    ALLOWED_ORIGINS: Optional[str] = None

    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "eu-central-1"
    AWS_BUCKET_NAME: Optional[str] = None
    AWS_ENDPOINT_URL: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()