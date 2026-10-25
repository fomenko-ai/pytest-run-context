import pytest

from context import ProjectContext
from pytest_run_context import RunContext, configure, with_run_context
from pytest_run_context.storage import SQLiteStorage
from settings import settings


@with_run_context(ProjectContext)
def require_prepared_environment(context: RunContext[ProjectContext]) -> None:
    if context.custom.environment != "prepared":
        raise ValueError("Prepare the environment before running pytest")


@pytest.fixture(scope="session", autouse=True)
def check_session_environment() -> None:
    require_prepared_environment()


def pytest_configure(config: pytest.Config) -> None:
    if not config.getoption("--run-id"):
        raise pytest.UsageError("Missing --run-id. Run environment preparation first.")
    configure(
        config,
        context_model=ProjectContext,
        storage=SQLiteStorage(settings.db),
    )
