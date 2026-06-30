"""Application settings loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    database_url: str = (
        "postgresql+asyncpg://tinder:tinder@localhost:5432/tinder"
    )
    redis_url: str = "redis://localhost:6379/0"
    app_port: int = 8000
    host: str = "0.0.0.0"
    log_level: str = "info"


settings = Settings()
