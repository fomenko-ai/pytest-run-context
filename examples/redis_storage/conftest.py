from typing import Optional

import pytest

from pytest_run_context import BaseCustomContext, RunInfo, configure
from pytest_run_context.storage import RedisStorage
from settings import settings


class ProjectContext(BaseCustomContext):
    environment: str = "local"
    lifecycle_event: str = "created"
    message: Optional[str] = None

    def on_run_start(self, info: RunInfo) -> None:
        self.lifecycle_event = "started"

    def on_run_finish(self, info: RunInfo) -> None:
        self.lifecycle_event = "finished"


def pytest_configure(config: pytest.Config) -> None:
    configure(
        config,
        context_model=ProjectContext,
        storage=RedisStorage.from_url(
            settings.url,
            port=settings.port,
            database=settings.db,
            username=settings.username,
            password=(settings.password.get_secret_value() if settings.password else None),
            ttl_seconds=settings.ttl,
            retry_count=settings.retries,
            retry_backoff_base=settings.backoff_base,
            retry_backoff_cap=settings.backoff_cap,
        ),
    )
