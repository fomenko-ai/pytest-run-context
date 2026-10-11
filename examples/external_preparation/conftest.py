import pytest

from context import ProjectContext
from pytest_run_context import configure
from pytest_run_context.storage import SQLiteStorage
from settings import settings


def pytest_configure(config: pytest.Config) -> None:
    if not config.getoption("--run-id"):
        raise pytest.UsageError("Missing --run-id. Run environment preparation first.")
    configure(
        config,
        context_model=ProjectContext,
        storage=SQLiteStorage(settings.db),
    )
