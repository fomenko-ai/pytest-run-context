from pytest_run_context import BaseCustomContext, RunInfo


class ProjectContext(BaseCustomContext):
    environment: str = "not prepared"
    tests_completed: bool = False
    cleanup_completed: bool = False

    def on_run_start(self, info: RunInfo) -> None:
        self.environment = "preparing"

    def on_run_finish(self, info: RunInfo) -> None:
        self.cleanup_completed = True
