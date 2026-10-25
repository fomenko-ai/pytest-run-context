from typing import Optional

import pytest

from pytest_run_context import BaseCustomContext, RunContext, RunInfo, configure, with_run_context
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


@with_run_context(ProjectContext)
def prepare_context(context: RunContext[ProjectContext], message: str) -> None:
    context.custom.message = message


@pytest.fixture(scope="session", autouse=True)
def prepare_session_context() -> None:
    prepare_context("prepared in conftest")


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
