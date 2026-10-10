from typing import NamedTuple, Optional, Protocol, runtime_checkable


class StoredRun(NamedTuple):
    info: str
    custom: str


class RunAlreadyExistsError(RuntimeError):
    pass


@runtime_checkable
class Storage(Protocol):
    def create_run(self, run_id: str, info: str, custom: str) -> None: ...
    def save_run(self, run_id: str, info: str, custom: str) -> None: ...
    def load_run(self, run_id: str) -> Optional[StoredRun]: ...
    def finish_run(self, run_id: str, info: str, custom: str) -> None: ...
    def close(self) -> None: ...
