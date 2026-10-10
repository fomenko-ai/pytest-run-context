from dataclasses import dataclass

import pytest

from .context import RunContext
from .errors import InvalidStoredRunError, RunAlreadyFinishedError, RunNotFoundError
from .models import BaseCustomContext
from .registry import _activate, _deactivate, get_run_context
from .storage import MemoryStorage, Storage


@dataclass(frozen=True)
class PluginSettings:
    context_model: type[BaseCustomContext]
    storage: Storage


_settings_key = pytest.StashKey[PluginSettings]()
_context_key = pytest.StashKey[RunContext]()
_token_key = pytest.StashKey[object]()
_owns_lifecycle_key = pytest.StashKey[bool]()


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
    requested_run_id = config.getoption("--run-id")
    try:
        if requested_run_id is None:
            context = RunContext.create(
                context_model=settings.context_model,
                storage=settings.storage,
            )
            owns_lifecycle = True
        else:
            context = RunContext.load(
                run_id=requested_run_id,
                context_model=settings.context_model,
                storage=settings.storage,
            )
            if context.info.finished_at is not None:
                raise RunAlreadyFinishedError(
                    f"RunContext {requested_run_id!r} is already finished"
                )
            owns_lifecycle = False
    except (InvalidStoredRunError, RunNotFoundError, RunAlreadyFinishedError) as exc:
        settings.storage.close()
        raise pytest.UsageError(str(exc)) from exc
    except BaseException:
        settings.storage.close()
        raise
    config.stash[_context_key] = context
    config.stash[_owns_lifecycle_key] = owns_lifecycle
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
        try:
            if config.stash[_owns_lifecycle_key]:
                context.finish()
            else:
                context.save()
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
