import pytest

from pytest_run_context import BaseCustomContext, RunContext, RunInfo, configure, with_run_context
from pytest_run_context.storage import MemoryStorage


class ProjectContext(BaseCustomContext):
    message: str = "not tested"
    lifecycle_event: str = "created"

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
    configure(config, context_model=ProjectContext, storage=MemoryStorage())
