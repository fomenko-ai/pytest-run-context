import os
from importlib import import_module
from typing import Optional

import pytest

from pytest_run_context import BaseCustomContext, RunInfo, configure
from pytest_run_context.storage import RedisStorage

import_module("dotenv").load_dotenv()


class ProjectContext(BaseCustomContext):
    environment: str = "local"
    lifecycle_event: str = "created"
    message: Optional[str] = None

    def on_run_start(self, info: RunInfo) -> None:
        self.lifecycle_event = "started"

    def on_run_finish(self, info: RunInfo) -> None:
        self.lifecycle_event = "finished"


def pytest_configure(config: pytest.Config) -> None:
    redis_url = os.environ.get("PYTEST_RUN_CONTEXT_REDIS_URL", "redis://localhost")
    port = int(os.environ.get("PYTEST_RUN_CONTEXT_REDIS_PORT", "6379"))
    database = int(os.environ.get("PYTEST_RUN_CONTEXT_REDIS_DB", "0"))
    username = os.environ.get("PYTEST_RUN_CONTEXT_REDIS_USERNAME") or None
    password = os.environ.get("PYTEST_RUN_CONTEXT_REDIS_PASSWORD") or None
    ttl_seconds = int(os.environ.get("PYTEST_RUN_CONTEXT_REDIS_TTL", "86400"))
    retry_count = int(os.environ.get("PYTEST_RUN_CONTEXT_REDIS_RETRIES", "3"))
    retry_backoff_base = float(
        os.environ.get("PYTEST_RUN_CONTEXT_REDIS_BACKOFF_BASE", "0.008")
    )
    retry_backoff_cap = float(
        os.environ.get("PYTEST_RUN_CONTEXT_REDIS_BACKOFF_CAP", "0.512")
    )
    configure(
        config,
        context_model=ProjectContext,
        storage=RedisStorage.from_url(
            redis_url,
            port=port,
            database=database,
            username=username,
            password=password,
            ttl_seconds=ttl_seconds,
            retry_count=retry_count,
            retry_backoff_base=retry_backoff_base,
            retry_backoff_cap=retry_backoff_cap,
        ),
    )
