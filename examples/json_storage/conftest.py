import os
from importlib import import_module
from pathlib import Path
from typing import Optional

import pytest

from pytest_run_context import BaseCustomContext, RunInfo, configure
from pytest_run_context.storage import JSONStorage

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
    directory = Path(
        os.environ.get(
            "PYTEST_RUN_CONTEXT_JSON_DIRECTORY",
            "/tmp/pytest-run-context-example/json",
        )
    )
    configure(
        config,
        context_model=ProjectContext,
        storage=JSONStorage(directory),
    )
