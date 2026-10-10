from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from .context import RunContext
from .models import BaseCustomContext, RunInfo
from .registry import _activate, _deactivate, get_run_context
from .storage import MemoryStorage, Storage


@dataclass(frozen=True)
class PluginSettings:
    context_model: type[BaseCustomContext]
    storage: Storage


_settings_key = pytest.StashKey[PluginSettings]()
_context_key = pytest.StashKey[RunContext]()
_token_key = pytest.StashKey[object]()


def configure(
    config: pytest.Config,
    *,
    context_model: type[BaseCustomContext] = BaseCustomContext,
    storage: Storage,
) -> None:
    if _settings_key in config.stash:
        raise RuntimeError("pytest_run_context is already configured")
    if not issubclass(context_model, BaseCustomContext):
        raise TypeError("context_model must inherit BaseCustomContext")
    if not isinstance(storage, Storage):
        raise TypeError("storage must implement Storage protocol")
    config.stash[_settings_key] = PluginSettings(context_model, storage)


def pytest_addoption(parser):
    group = parser.getgroup("run-context")
    group.addoption(
        "--run-id", action="store", default=None, help="Explicit unique run ID"
    )


def pytest_sessionstart(session):
    config = session.config
    settings = config.stash.get(_settings_key, None)
    if settings is None:
        settings = PluginSettings(BaseCustomContext, MemoryStorage())
    info = RunInfo(
        run_id=config.getoption("--run-id") or str(uuid4()),
        started_at=datetime.now(timezone.utc),
    )
    custom = settings.context_model()
    context = RunContext(info, custom, settings.storage)
    custom.on_run_start(info)
    settings.storage.create_run(
        info.run_id, info.model_dump_json(), custom.model_dump_json()
    )
    config.stash[_context_key] = context
    config.stash[_token_key] = _activate(context)


@pytest.fixture(scope="session")
def run_context():
    return get_run_context()


def pytest_sessionfinish(session, exitstatus):
    config = session.config
    if _context_key not in config.stash:
        return
    context = config.stash[_context_key]
    try:
        final_info = RunInfo.model_validate(
            {**context.info.model_dump(), "finished_at": datetime.now(timezone.utc)}
        )
        try:
            context._finish(final_info)
        except Exception as exc:
            session.exitstatus = pytest.ExitCode.INTERNAL_ERROR
            raise pytest.UsageError(
                f"pytest_run_context final save failed: {exc}"
            ) from exc
    finally:
        _deactivate(config.stash[_token_key])
        settings = config.stash.get(_settings_key, None)
        if settings is not None:
            settings.storage.close()
        else:
            context._storage.close()
