from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parents[2] / ".env",
        env_prefix="PYTEST_RUN_CONTEXT_REDIS_",
        env_ignore_empty=True,
        extra="ignore",
    )

    url: str = "redis://localhost"
    port: int = 6379
    db: int = 0
    username: str | None = None
    password: SecretStr | None = None
    ttl: int = 86_400
    retries: int = 3
    backoff_base: float = 0.008
    backoff_cap: float = 0.512


settings = RedisSettings()
