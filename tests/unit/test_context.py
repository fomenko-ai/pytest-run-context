from datetime import datetime, timezone
from uuid import UUID

import pytest

from pytest_run_context import (
    BaseCustomContext,
    InvalidStoredRunError,
    RunAlreadyFinishedError,
    RunContext,
    RunInfo,
    RunNotFoundError,
    get_run_context,
)
from pytest_run_context.registry import _activate, _current, _deactivate
from pytest_run_context.storage import MemoryStorage, RunAlreadyExistsError, StoredRun


class LifecycleContext(BaseCustomContext):
    value: int = 0
    started: int = 0
    finished: int = 0

    def on_run_start(self, info: RunInfo) -> None:
        self.started += 1
        self.value = 1

    def on_run_finish(self, info: RunInfo) -> None:
        assert info.finished_at is not None
        self.finished += 1
        self.value = 2


class FailingFinishContext(BaseCustomContext):
    changed: bool = False

    def on_run_finish(self, info: RunInfo) -> None:
        self.changed = True
        raise RuntimeError("hook failed")


class FailingFinishStorage(MemoryStorage):
    def finish_run(self, run_id: str, info: str, custom: str) -> None:
        raise OSError("storage failed")


def make_info(*, finished: bool = False) -> RunInfo:
    return RunInfo(
        run_id="run-1",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        finished_at=datetime(2026, 1, 2, tzinfo=timezone.utc) if finished else None,
    )


def test_create_generates_uuid_invokes_start_and_persists() -> None:
    storage = MemoryStorage()

    context = RunContext.create(context_model=LifecycleContext, storage=storage)

    assert UUID(context.info.run_id)
    assert context.info.finished_at is None
    assert context.custom.started == 1
    assert context.custom.value == 1
    assert storage.load_run(context.info.run_id) == StoredRun(
        context.info.model_dump_json(), context.custom.model_dump_json()
    )


def test_create_accepts_explicit_id_and_rejects_duplicate_atomically() -> None:
    storage = MemoryStorage()
    first = RunContext.create(
        context_model=LifecycleContext, storage=storage, run_id="chosen-id"
    )

    with pytest.raises(RunAlreadyExistsError, match="chosen-id"):
        RunContext.create(
            context_model=LifecycleContext, storage=storage, run_id="chosen-id"
        )

    stored = storage.load_run("chosen-id")
    assert stored is not None
    assert stored.info == first.info.model_dump_json()


def test_load_restores_info_and_custom_without_start_hook() -> None:
    storage = MemoryStorage()
    created = RunContext.create(
        context_model=LifecycleContext, storage=storage, run_id="run-1"
    )
    created.custom.value = 7
    created.save()

    loaded = RunContext.load(
        run_id="run-1", context_model=LifecycleContext, storage=storage
    )

    assert loaded.info == created.info
    assert loaded.custom.value == 7
    assert loaded.custom.started == 1


def test_load_missing_run_fails_clearly() -> None:
    with pytest.raises(RunNotFoundError, match="missing"):
        RunContext.load(
            run_id="missing",
            context_model=LifecycleContext,
            storage=MemoryStorage(),
        )


@pytest.mark.parametrize(
    ("info", "custom", "message"),
    [
        ("not-json", "{}", "RunInfo"),
        (make_info().model_dump_json(), '{"value":"invalid"}', "custom context"),
        (
            RunInfo(
                run_id="different",
                started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ).model_dump_json(),
            "{}",
            "does not match",
        ),
    ],
)
def test_load_rejects_invalid_stored_data(info: str, custom: str, message: str) -> None:
    storage = MemoryStorage()
    storage.create_run("run-1", info, custom)

    with pytest.raises(InvalidStoredRunError, match=message):
        RunContext.load(run_id="run-1", context_model=LifecycleContext, storage=storage)


def test_loaded_context_can_be_modified_and_saved() -> None:
    storage = MemoryStorage()
    RunContext.create(context_model=LifecycleContext, storage=storage, run_id="run-1")
    loaded = RunContext.load(
        run_id="run-1", context_model=LifecycleContext, storage=storage
    )

    loaded.custom.value = 9
    loaded.save()

    restored = RunContext.load(
        run_id="run-1", context_model=LifecycleContext, storage=storage
    )
    assert restored.custom.value == 9


def test_finish_preserves_custom_identity_and_persists_hook_changes() -> None:
    storage = MemoryStorage()
    context = RunContext.create(
        context_model=LifecycleContext, storage=storage, run_id="run-1"
    )
    custom = context.custom

    context.finish()

    assert context.custom is custom
    assert context.info.finished_at is not None
    assert context.custom.finished == 1
    restored = RunContext.load(
        run_id="run-1", context_model=LifecycleContext, storage=storage
    )
    assert restored.info.finished_at == context.info.finished_at
    assert restored.custom.value == 2
    assert restored.custom.finished == 1


def test_finish_hook_failure_does_not_apply_info_or_persist() -> None:
    storage = MemoryStorage()
    context = RunContext.create(
        context_model=FailingFinishContext, storage=storage, run_id="run-1"
    )
    before = storage.load_run("run-1")

    with pytest.raises(RuntimeError, match="hook failed"):
        context.finish()

    assert context.info.finished_at is None
    assert context.custom.changed is True
    assert storage.load_run("run-1") == before


def test_finish_storage_failure_is_propagated() -> None:
    storage = FailingFinishStorage()
    context = RunContext.create(
        context_model=LifecycleContext, storage=storage, run_id="run-1"
    )

    with pytest.raises(OSError, match="storage failed"):
        context.finish()

    assert context.info.finished_at is not None
    assert context.custom.finished == 1
    stored = storage.load_run("run-1")
    assert stored is not None
    assert RunInfo.model_validate_json(stored.info).finished_at is None


def test_finish_rejects_already_finished_context() -> None:
    storage = MemoryStorage()
    context = RunContext.create(
        context_model=LifecycleContext, storage=storage, run_id="run-1"
    )
    context.finish()

    with pytest.raises(RunAlreadyFinishedError, match="already finished"):
        context.finish()

    assert context.custom.finished == 1


def test_load_allows_finished_context() -> None:
    storage = MemoryStorage()
    context = RunContext.create(
        context_model=LifecycleContext, storage=storage, run_id="run-1"
    )
    context.finish()

    loaded = RunContext.load(
        run_id="run-1", context_model=LifecycleContext, storage=storage
    )

    assert loaded.info.finished_at is not None


def test_get_run_context_fails_outside_active_session() -> None:
    token = _current.set(None)
    try:
        with pytest.raises(RuntimeError, match="outside an active pytest session"):
            get_run_context()
    finally:
        _current.reset(token)


def test_registry_activation_returns_same_context_and_restores_previous() -> None:
    outer = RunContext(make_info(), LifecycleContext(), MemoryStorage())
    inner = RunContext(make_info(), LifecycleContext(), MemoryStorage())
    outer_token = _activate(outer)

    try:
        assert get_run_context() is outer
        inner_token = _activate(inner)
        try:
            assert get_run_context() is inner
        finally:
            _deactivate(inner_token)
        assert get_run_context() is outer
    finally:
        _deactivate(outer_token)
