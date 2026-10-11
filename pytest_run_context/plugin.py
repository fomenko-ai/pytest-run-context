from contextvars import Token
from dataclasses import dataclass
from typing import Optional, Protocol, Union

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


class _XdistNode(Protocol):
    config: pytest.Config
    workerinput: dict[str, object]


_settings_key = pytest.StashKey[PluginSettings]()
_context_key = pytest.StashKey[RunContext]()
_token_key = pytest.StashKey[Token[Optional[RunContext]]]()
_owns_lifecycle_key = pytest.StashKey[bool]()
_xdist_controller_key = pytest.StashKey[bool]()
_worker_run_id_key = "pytest_run_context_run_id"


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


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("run-context")
    group.addoption("--run-id", action="store", default=None, help="Explicit unique run ID")


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session: pytest.Session) -> None:
    config = session.config
    settings = config.stash.get(_settings_key, None)
    if settings is None:
        settings = PluginSettings(BaseCustomContext, MemoryStorage())
    worker_input = getattr(config, "workerinput", None)
    worker_run_id = worker_input.get(_worker_run_id_key) if worker_input is not None else None
    requested_run_id = worker_run_id or config.getoption("--run-id")
    try:
        if worker_run_id is not None and isinstance(settings.storage, MemoryStorage):
            raise pytest.UsageError(
                "pytest-xdist requires Storage shared by the controller and workers; "
                "MemoryStorage cannot be used with multiple processes"
            )
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


@pytest.hookimpl(optionalhook=True)
def pytest_configure_node(node: _XdistNode) -> None:
    config = node.config
    context = config.stash[_context_key]
    if isinstance(context._storage, MemoryStorage):
        raise pytest.UsageError(
            "pytest-xdist requires Storage shared by the controller and workers; "
            "MemoryStorage cannot be used with multiple processes"
        )
    config.stash[_xdist_controller_key] = True
    node.workerinput[_worker_run_id_key] = context.info.run_id


@pytest.fixture(scope="session")
def run_context() -> RunContext:
    return get_run_context()


def pytest_sessionfinish(
    session: pytest.Session,
    exitstatus: Union[int, pytest.ExitCode],
) -> None:
    config = session.config
    if _context_key not in config.stash:
        return
    context = config.stash[_context_key]
    try:
        try:
            if config.stash[_owns_lifecycle_key]:
                if config.stash.get(_xdist_controller_key, False):
                    settings = config.stash.get(_settings_key, None)
                    storage = settings.storage if settings is not None else context._storage
                    context = RunContext.load(
                        run_id=context.info.run_id,
                        context_model=type(context.custom),
                        storage=storage,
                    )
                context.finish()
        except Exception as exc:
            session.exitstatus = pytest.ExitCode.INTERNAL_ERROR
            raise pytest.UsageError(f"pytest_run_context final save failed: {exc}") from exc
    finally:
        _deactivate(config.stash[_token_key])
        settings = config.stash.get(_settings_key, None)
        if settings is not None:
            settings.storage.close()
        else:
            context._storage.close()
