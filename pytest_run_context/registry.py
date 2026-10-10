from contextvars import ContextVar, Token
from typing import Optional

from .context import RunContext

_current: ContextVar[Optional[RunContext]] = ContextVar(
    "pytest_run_context", default=None
)


def get_run_context() -> RunContext:
    context = _current.get()
    if context is None:
        raise RuntimeError("RunContext is unavailable outside an active pytest session")
    return context


def _activate(context: RunContext) -> Token:
    return _current.set(context)


def _deactivate(token: Token) -> None:
    _current.reset(token)
