from typing import Optional

from .base import RunAlreadyExistsError, StoredRun


class MemoryStorage:
    def __init__(self) -> None:
        self._runs: dict[str, StoredRun] = {}

    def create_run(self, run_id: str, info: str, custom: str) -> None:
        if run_id in self._runs:
            raise RunAlreadyExistsError(run_id)
        self._runs[run_id] = StoredRun(info, custom)

    def save_run(self, run_id: str, info: str, custom: str) -> None:
        if run_id not in self._runs:
            raise KeyError(run_id)
        self._runs[run_id] = StoredRun(info, custom)

    def load_run(self, run_id: str) -> Optional[StoredRun]:
        return self._runs.get(run_id)

    def finish_run(self, run_id: str, info: str, custom: str) -> None:
        self.save_run(run_id, info, custom)

    def close(self) -> None:
        pass
