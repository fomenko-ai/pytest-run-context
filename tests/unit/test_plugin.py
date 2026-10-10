from types import SimpleNamespace
from typing import Any, cast

import pytest
from pydantic import PrivateAttr

from pytest_run_context import BaseCustomContext, RunInfo, plugin
from pytest_run_context.storage import MemoryStorage

pytest_plugins = ["pytester"]


class FakeConfig:
    def __init__(self) -> None:
        self.stash = pytest.Stash()


class RecordingContext(BaseCustomContext):
    value: int = 0
    _events: list[str] = PrivateAttr(default_factory=list)

    def on_run_start(self, info: RunInfo) -> None:
        self._events.append(f"start:{info.run_id}")
        self.value = 1

    def on_run_finish(self, info: RunInfo) -> None:
        self._events.append(f"finish:{info.run_id}")
        self.value = 2


class RecordingStorage(MemoryStorage):
    def __init__(self, *, fail_finish: bool = False) -> None:
        super().__init__()
        self.closed = False
        self.fail_finish = fail_finish

    def finish_run(self, run_id: str, info: str, custom: str) -> None:
        if self.fail_finish:
            raise OSError("cannot persist")
        super().finish_run(run_id, info, custom)

    def close(self) -> None:
        self.closed = True


def test_configure_stores_settings() -> None:
    config = FakeConfig()
    pytest_config = cast(pytest.Config, config)
    storage = MemoryStorage()

    plugin.configure(pytest_config, context_model=RecordingContext, storage=storage)

    settings = config.stash[plugin._settings_key]
    assert settings.context_model is RecordingContext
    assert settings.storage is storage


def test_configure_rejects_repeated_configuration() -> None:
    config = FakeConfig()
    pytest_config = cast(pytest.Config, config)
    plugin.configure(pytest_config, storage=MemoryStorage())

    with pytest.raises(RuntimeError, match="already configured"):
        plugin.configure(pytest_config, storage=MemoryStorage())


@pytest.mark.parametrize(
    ("context_model", "storage", "message"),
    [
        (object, MemoryStorage(), "context_model must inherit"),
        (BaseCustomContext, object(), "storage must implement"),
    ],
)
def test_configure_rejects_invalid_dependencies(
    context_model: Any,
    storage: Any,
    message: str,
) -> None:
    config = FakeConfig()
    pytest_config = cast(pytest.Config, config)
    with pytest.raises(TypeError, match=message):
        plugin.configure(pytest_config, context_model=context_model, storage=storage)


def test_addoption_registers_run_id_option(pytestconfig: pytest.Config) -> None:
    assert pytestconfig.getoption("--run-id") is None


def test_plugin_uses_default_context_and_generated_id(
    pytester: pytest.Pytester,
) -> None:
    pytester.makepyfile(
        """
        from uuid import UUID
        from pytest_run_context import BaseCustomContext, get_run_context

        def test_default_context(run_context):
            assert run_context is get_run_context()
            assert type(run_context.custom) is BaseCustomContext
            assert UUID(run_context.info.run_id)
        """
    )

    result = pytester.runpytest()

    result.assert_outcomes(passed=1)


def test_configured_plugin_lifecycle_and_explicit_save(
    pytester: pytest.Pytester,
) -> None:
    pytester.makeconftest(
        """
        from pydantic import PrivateAttr
        from pytest_run_context import BaseCustomContext, configure
        from pytest_run_context.storage import MemoryStorage

        class CustomContext(BaseCustomContext):
            value: int = 0
            _events: list[str] = PrivateAttr(default_factory=list)

            def on_run_start(self, info):
                self._events.append("start")
                self.value = 1

            def on_run_finish(self, info):
                self._events.append("finish")
                self.value = 3

        storage = MemoryStorage()

        def pytest_configure(config):
            configure(config, context_model=CustomContext, storage=storage)

        def pytest_unconfigure(config):
            context = config.stash[__import__("pytest_run_context.plugin", fromlist=["_context_key"])._context_key]
            assert context.custom._events == ["start", "finish"]
            saved = storage.load_run("chosen-id")
            assert saved is not None
            assert '"finished_at":"' in saved.info
            assert saved.custom == '{"value":3}'
        """
    )
    pytester.makepyfile(
        """
        from pytest_run_context import get_run_context

        def test_context(run_context):
            assert run_context is get_run_context()
            assert run_context.info.run_id == "chosen-id"
            assert run_context.custom.value == 1
            run_context.custom.value = 2
            run_context.save()
        """
    )

    result = pytester.runpytest("--run-id", "chosen-id")

    result.assert_outcomes(passed=1)


def test_initialization_failure_does_not_create_active_context(
    pytester: pytest.Pytester,
) -> None:
    pytester.makeconftest(
        """
        from pytest_run_context import BaseCustomContext, configure
        from pytest_run_context.storage import MemoryStorage

        class InvalidContext(BaseCustomContext):
            required: str

        def pytest_configure(config):
            configure(config, context_model=InvalidContext, storage=MemoryStorage())
        """
    )
    pytester.makepyfile("def test_never_runs(): pass")

    result = pytester.runpytest()

    assert result.ret != 0
    result.stdout.fnmatch_lines(
        ["*ValidationError: 1 validation error for InvalidContext*"]
    )


def test_final_save_failure_fails_run_and_closes_storage(
    pytester: pytest.Pytester,
) -> None:
    pytester.makeconftest(
        """
        from pytest_run_context import configure
        from pytest_run_context.storage import MemoryStorage

        class FailingStorage(MemoryStorage):
            def finish_run(self, run_id, info, custom):
                raise OSError("cannot persist")

            def close(self):
                print("STORAGE_CLOSED")

        def pytest_configure(config):
            configure(config, storage=FailingStorage())
        """
    )
    pytester.makepyfile("def test_passes(): pass")

    result = pytester.runpytest()

    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stdout.fnmatch_lines(["*STORAGE_CLOSED*"])
    result.stderr.fnmatch_lines(
        ["*pytest_run_context final save failed: cannot persist*"]
    )


def test_sessionfinish_without_initialized_context_is_noop() -> None:
    config = FakeConfig()
    session = SimpleNamespace(config=config, exitstatus=pytest.ExitCode.OK)

    plugin.pytest_sessionfinish(session, pytest.ExitCode.OK)  # type: ignore[arg-type]

    assert session.exitstatus == pytest.ExitCode.OK
