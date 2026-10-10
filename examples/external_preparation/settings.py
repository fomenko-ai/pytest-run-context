import os
from pathlib import Path

DATABASE = Path(
    os.environ.get(
        "PYTEST_RUN_CONTEXT_EXTERNAL_DB",
        "/tmp/pytest-run-context-external-preparation.sqlite3",
    )
)
