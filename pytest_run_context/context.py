from datetime import datetime, timezone
from typing import Generic, Optional, TypeVar
from uuid import uuid4

from pydantic import ValidationError

from .errors import InvalidStoredRunError, RunAlreadyFinishedError, RunNotFoundError
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

    @classmethod
    def create(
        cls,
        *,
        context_model: type[T],
        storage: Storage,
        run_id: Optional[str] = None,
    ) -> "RunContext[T]":
        info = RunInfo(
            run_id=run_id if run_id is not None else str(uuid4()),
            started_at=datetime.now(timezone.utc),
        )
        custom = context_model()
        custom.on_run_start(info)
        storage.create_run(
            info.run_id,
            info.model_dump_json(),
            custom.model_dump_json(),
        )
        return cls(info, custom, storage)

    @classmethod
    def load(
        cls,
        *,
        run_id: str,
        context_model: type[T],
        storage: Storage,
    ) -> "RunContext[T]":
        stored = storage.load_run(run_id)
        if stored is None:
            raise RunNotFoundError(f"RunContext {run_id!r} was not found")

        try:
            info = RunInfo.model_validate_json(stored.info)
        except ValidationError as exc:
            raise InvalidStoredRunError(
                f"Stored RunInfo for run {run_id!r} is invalid"
            ) from exc
        if info.run_id != run_id:
            raise InvalidStoredRunError(
                f"Stored RunInfo ID {info.run_id!r} does not match requested run {run_id!r}"
            )

        try:
            custom = context_model.model_validate_json(stored.custom)
        except ValidationError as exc:
            raise InvalidStoredRunError(
                f"Stored custom context for run {run_id!r} is invalid"
            ) from exc
        return cls(info, custom, storage)

    def save(self) -> None:
        self._storage.save_run(
            self._info.run_id,
            self._info.model_dump_json(),
            self._custom.model_dump_json(),
        )

    def finish(self) -> None:
        if self._info.finished_at is not None:
            raise RunAlreadyFinishedError(
                f"RunContext {self._info.run_id!r} is already finished"
            )
        final_info = RunInfo.model_validate(
            {
                **self._info.model_dump(),
                "finished_at": datetime.now(timezone.utc),
            }
        )
        self._custom.on_run_finish(final_info)
        self._info = final_info
        self._storage.finish_run(
            final_info.run_id,
            final_info.model_dump_json(),
            self._custom.model_dump_json(),
        )
