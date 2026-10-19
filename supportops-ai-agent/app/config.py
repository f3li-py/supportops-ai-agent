from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    app_env: str = "development"
    database_url: str = "sqlite:///./supportops.db"
    host: str = "127.0.0.1"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance to avoid reading .env multiple times."""
    return Settings()
