from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from pytest_run_context import (
    BaseCustomContext,
    RunContext,
    RunInfo,
    get_run_context,
    with_run_context,
)
from pytest_run_context.registry import _activate, _current, _deactivate
from pytest_run_context.storage import MemoryStorage

pytest_plugins = ["pytester"]


class ProjectContext(BaseCustomContext):
    environment: str = "dev"
    starts: int = 0
    finishes: int = 0

    def on_run_start(self, info: RunInfo) -> None:
        self.starts += 1

    def on_run_finish(self, info: RunInfo) -> None:
        self.finishes += 1


class ExtendedContext(ProjectContext):
    region: str = "local"


@pytest.fixture
def active_context() -> Iterator[RunContext[ProjectContext]]:
    storage = MemoryStorage()
    context = RunContext.create(context_model=ProjectContext, storage=storage)
    token = _activate(context)
    try:
        yield context
    finally:
        _deactivate(token)
        storage.close()


def test_injection_preserves_identity_arguments_result_and_metadata(
    active_context: RunContext[ProjectContext],
) -> None:
    @with_run_context(ProjectContext)
    def update(
        context: RunContext[ProjectContext],
        environment: str,
        /,
        *labels: str,
        suffix: str = "ready",
        **values: int,
    ) -> tuple[ProjectContext, str]:
        """Update the active model."""
        assert context is active_context is get_run_context()
        context.custom.environment = environment
        return context.custom, f"{labels[0]}-{suffix}-{values['attempt']}"

    model, result = update("stage", "setup", suffix="done", attempt=2)

    assert model is active_context.custom
    assert model.environment == "stage"
    assert result == "setup-done-2"
    assert update.__name__ == "update"
    assert update.__doc__ == "Update the active model."


def test_decoration_before_activation_and_fresh_lookup_on_each_call() -> None:
    outer_token = _current.set(None)
    storage = MemoryStorage()
    try:

        @with_run_context(ProjectContext)
        def current(context: RunContext[ProjectContext]) -> RunContext[ProjectContext]:
            return context

        with pytest.raises(RuntimeError, match="outside an active pytest session"):
            current()

        for _ in range(2):
            context = RunContext.create(context_model=ProjectContext, storage=storage)
            token = _activate(context)
            try:
                assert current() is context
            finally:
                _deactivate(token)

        with pytest.raises(RuntimeError, match="outside an active pytest session"):
            current()
    finally:
        _current.reset(outer_token)
        storage.close()


def test_expected_model_accepts_subclasses() -> None:
    storage = MemoryStorage()
    context = RunContext.create(context_model=ExtendedContext, storage=storage)
    token = _activate(context)
    try:

        @with_run_context(ProjectContext)
        def model(context: RunContext[ProjectContext]) -> ProjectContext:
            return context.custom

        assert model() is context.custom
    finally:
        _deactivate(token)
        storage.close()


def test_wrong_model_rejected_before_helper_body(
    active_context: RunContext[ProjectContext],
) -> None:
    called = False

    @with_run_context(ExtendedContext)
    def requires_region(context: RunContext[ExtendedContext]) -> str:
        nonlocal called
        called = True
        return context.custom.region

    with pytest.raises(TypeError, match="Expected custom context of type ExtendedContext"):
        requires_region()

    assert not called
    assert active_context.custom.environment == "dev"


@pytest.mark.parametrize("invalid_model", [None, object, ProjectContext()])
def test_invalid_model_rejected_at_decoration(
    invalid_model: Any,  # noqa: ANN401 - exercise invalid public API inputs
) -> None:
    with pytest.raises(TypeError, match="context_model must inherit BaseCustomContext"):
        with_run_context(invalid_model)


def test_only_explicit_save_persists_and_no_lifecycle_callbacks_are_added() -> None:
    storage = MemoryStorage()
    context = RunContext.create(context_model=ProjectContext, storage=storage)
    initial = storage.load_run(context.info.run_id)
    token = _activate(context)
    try:

        @with_run_context(ProjectContext)
        def update(context: RunContext[ProjectContext], *, persist: bool = False) -> None:
            context.custom.environment = "stage"
            if persist:
                context.save()

        update()
        assert context.custom.environment == "stage"
        assert storage.load_run(context.info.run_id) == initial
        update(persist=True)
        stored = storage.load_run(context.info.run_id)
        assert stored is not None
        assert ProjectContext.model_validate_json(stored.custom).environment == "stage"
        assert context.custom.starts == 1
        assert context.custom.finishes == 0
        assert context.info.finished_at is None
    finally:
        _deactivate(token)
        storage.close()


def test_helper_exception_propagates_without_rollback(
    active_context: RunContext[ProjectContext],
) -> None:
    failure = ValueError("environment unavailable")

    @with_run_context(ProjectContext)
    def fail(context: RunContext[ProjectContext]) -> None:
        context.custom.environment = "stage"
        raise failure

    with pytest.raises(ValueError, match="environment unavailable") as raised:
        fail()

    assert raised.value is failure
    assert active_context.custom.environment == "stage"


def test_conftest_fixture_calls_helper_while_tests_use_fixture(pytester: pytest.Pytester) -> None:
    pytester.makeconftest(
        """
        import pytest
        from pytest_run_context import BaseCustomContext, RunContext, configure, with_run_context
        from pytest_run_context.storage import MemoryStorage

        class ProjectContext(BaseCustomContext):
            environment: str = "dev"

        @with_run_context(ProjectContext)
        def prepare(context: RunContext[ProjectContext], environment: str) -> None:
            context.custom.environment = environment

        def pytest_configure(config: pytest.Config) -> None:
            configure(config, context_model=ProjectContext, storage=MemoryStorage())
            with pytest.raises(RuntimeError, match="outside an active pytest session"):
                prepare("too early")

        @pytest.fixture(scope="session", autouse=True)
        def prepare_session() -> None:
            prepare("stage")
        """
    )
    pytester.makepyfile(
        """
        from pytest_run_context import RunContext, get_run_context

        def test_context(run_context: RunContext) -> None:
            assert run_context is get_run_context()
            assert run_context.custom.environment == "stage"
        """
    )

    result = pytester.runpytest_subprocess("--strict-markers")

    result.assert_outcomes(passed=1)
