from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from pytest_run_context import BaseCustomContext, RunInfo


def make_info() -> RunInfo:
    return RunInfo(run_id="run-1", started_at=datetime(2026, 1, 1, tzinfo=timezone.utc))


def test_run_info_is_frozen() -> None:
    info = make_info()

    with pytest.raises(ValidationError, match="frozen"):
        info.run_id = "changed"  # ty: ignore[invalid-assignment]


def test_run_info_defaults_finished_at_to_none() -> None:
    assert make_info().finished_at is None


def test_base_custom_context_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        BaseCustomContext.model_validate({"unexpected": True})


def test_custom_context_validates_assignment() -> None:
    class CustomContext(BaseCustomContext):
        count: int = 0

    context = CustomContext()

    with pytest.raises(ValidationError):
        context.count = "invalid"  # ty: ignore[invalid-assignment]


def test_default_lifecycle_callbacks_are_noops() -> None:
    context = BaseCustomContext()
    info = make_info()

    assert context.on_run_start(info) is None
    assert context.on_run_finish(info) is None
