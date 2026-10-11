from context import ProjectContext
from pytest_run_context import RunContext
from pytest_run_context.storage import SQLiteStorage
from settings import settings


def main() -> None:
    settings.db.parent.mkdir(parents=True, exist_ok=True)
    storage = SQLiteStorage(settings.db)
    try:
        context = RunContext.create(context_model=ProjectContext, storage=storage)
        context.custom.environment = "prepared"
        context.save()
        print(context.info.run_id)
    finally:
        storage.close()


if __name__ == "__main__":
    main()
