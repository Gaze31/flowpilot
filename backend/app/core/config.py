"""App settings, read from environment variables / .env. Done."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "FlowPilot"
    database_url: str = "postgresql+asyncpg://flowpilot:flowpilot@localhost:5432/flowpilot"
    redis_url: str = "redis://localhost:6379/0"
    db_null_pool: bool = False  # tests set this to avoid sharing connections across event loops

    queue_name: str = "flowpilot:runs"
    max_attempts: int = 3  # per node, including the first try
    backoff_base_seconds: float = 1.0  # waits 1s, 2s, 4s ... between attempts

    cors_origins: list[str] = ["http://localhost:3000"]

    # Week 3
    llm_api_key: str | None = None
    llm_model: str = "set-your-model-name"
    llm_timeout_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
