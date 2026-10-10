from datetime import datetime, timezone

import pytest

from pytest_run_context import BaseCustomContext, RunContext, RunInfo, get_run_context
from pytest_run_context.registry import _activate, _current, _deactivate
from pytest_run_context.storage import MemoryStorage, StoredRun


class LifecycleContext(BaseCustomContext):
    finished: bool = False

    def on_run_finish(self, info: RunInfo) -> None:
        self.finished = info.finished_at is not None


def make_info(*, finished: bool = False) -> RunInfo:
    return RunInfo(
        run_id="run-1",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        finished_at=datetime(2026, 1, 2, tzinfo=timezone.utc) if finished else None,
    )


def test_context_exposes_same_objects_and_saves_snapshot() -> None:
    info = make_info()
    custom = LifecycleContext()
    storage = MemoryStorage()
    storage.create_run(info.run_id, "initial-info", "initial-custom")
    context = RunContext(info, custom, storage)

    custom.finished = True
    context.save()

    assert context.info is info
    assert context.custom is custom
    assert storage.load_run(info.run_id) == StoredRun(
        info.model_dump_json(), custom.model_dump_json()
    )


def test_finish_updates_info_invokes_callback_and_persists() -> None:
    initial_info = make_info()
    final_info = make_info(finished=True)
    custom = LifecycleContext()
    storage = MemoryStorage()
    storage.create_run(initial_info.run_id, "initial-info", "initial-custom")
    context = RunContext(initial_info, custom, storage)

    context._finish(final_info)

    assert context.info is final_info
    assert custom.finished is True
    assert storage.load_run(final_info.run_id) == StoredRun(
        final_info.model_dump_json(), custom.model_dump_json()
    )


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
