from typing import Generic, TypeVar

from .models import BaseCustomContext, RunInfo
from .storage import Storage

T = TypeVar("T", bound=BaseCustomContext)


class RunContext(Generic[T]):
    def __init__(self, info: RunInfo, custom: T, storage: Storage) -> None:
        self._info = info
        self._custom = custom
        self._storage = storage

    @property
    def info(self) -> RunInfo:
        return self._info

    @property
    def custom(self) -> T:
        return self._custom

    def save(self) -> None:
        self._storage.save_run(
            self._info.run_id,
            self._info.model_dump_json(),
            self._custom.model_dump_json(),
        )

    def _finish(self, info: RunInfo) -> None:
        self._info = info
        self._custom.on_run_finish(info)
        self._storage.finish_run(
            info.run_id, info.model_dump_json(), self._custom.model_dump_json()
        )
