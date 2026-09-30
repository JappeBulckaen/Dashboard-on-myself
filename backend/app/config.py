from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the project paths from this file so configuration does not depend on the shell's working directory.
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from the project-root .env file or environment."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str


@lru_cache
def get_settings() -> Settings:
    """Load settings once and reuse them throughout the process."""
    return Settings()
