import sys

from context import ProjectContext
from pytest_run_context import RunContext
from pytest_run_context.storage import SQLiteStorage
from settings import settings


def main(run_id: str) -> None:
    storage = SQLiteStorage(settings.db)
    try:
        context = RunContext.load(
            run_id=run_id,
            context_model=ProjectContext,
            storage=storage,
        )
        context.finish()
    finally:
        storage.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: cleanup.py RUN_ID")
    main(sys.argv[1])
