"""Application configuration using Pydantic Settings.

Reads configuration from environment variables or a local `.env` file,
with sensible defaults for database location and timezone.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime application settings."""

    DATABASE_URL: str = "sqlite:///./data/study.db"
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"
    DEMO_MODE: bool = False
    DEMO_MAX_SESSIONS: int = 1000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
