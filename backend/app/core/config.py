"""App settings, read from environment variables / .env. Done."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_EMAIL_FROM = "FlowPilot <onboarding@resend.dev>"


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
    api_key: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "set-your-model-name"
    llm_timeout_seconds: float = 30.0

    # Email: Resend is used only when resend_api_key is set, otherwise emails are just logged
    resend_api_key: str | None = None
    email_from: str = DEFAULT_EMAIL_FROM
    email_timeout_seconds: float = 15.0

    @field_validator("email_from", mode="before")
    @classmethod
    def _blank_email_from_means_default(cls, value: object) -> object:
        # An empty `EMAIL_FROM=` line in .env (like the template) should not wipe out the default
        if value is None or (isinstance(value, str) and not value.strip()):
            return DEFAULT_EMAIL_FROM
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
