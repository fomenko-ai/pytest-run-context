import os
from importlib import import_module
from pathlib import Path
from typing import Optional

import pytest

from pytest_run_context import BaseCustomContext, RunInfo, configure
from pytest_run_context.storage import SQLiteStorage

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
    database = Path(
        os.environ.get(
            "PYTEST_RUN_CONTEXT_SQLITE_PATH",
            "/tmp/pytest-run-context-example/runs.sqlite3",
        )
    )
    database.parent.mkdir(parents=True, exist_ok=True)
    configure(
        config,
        context_model=ProjectContext,
        storage=SQLiteStorage(database),
    )
