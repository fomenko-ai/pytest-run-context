import pytest

from pytest_run_context import BaseCustomContext, RunInfo, configure
from pytest_run_context.storage import MemoryStorage


class ProjectContext(BaseCustomContext):
    message: str = "not tested"
    lifecycle_event: str = "created"

    def on_run_start(self, info: RunInfo) -> None:
        self.lifecycle_event = "started"

    def on_run_finish(self, info: RunInfo) -> None:
        self.lifecycle_event = "finished"


def pytest_configure(config: pytest.Config) -> None:
    configure(config, context_model=ProjectContext, storage=MemoryStorage())
