from context import ProjectContext
from settings import DATABASE

from pytest_run_context import RunContext
from pytest_run_context.storage import SQLiteStorage


def main() -> None:
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    storage = SQLiteStorage(DATABASE)
    try:
        context = RunContext.create(context_model=ProjectContext, storage=storage)
        context.custom.environment = "prepared"
        context.save()
        print(context.info.run_id)
    finally:
        storage.close()


if __name__ == "__main__":
    main()
