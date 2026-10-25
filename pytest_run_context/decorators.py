from __future__ import annotations

import sys
from collections.abc import Callable
from functools import wraps
from typing import TypeVar, cast

from .context import RunContext
from .models import BaseCustomContext
from .registry import get_run_context

if sys.version_info >= (3, 10):
    from typing import Concatenate, ParamSpec
else:
    from typing_extensions import Concatenate, ParamSpec

T = TypeVar("T", bound=BaseCustomContext)
P = ParamSpec("P")
R = TypeVar("R")


def with_run_context(
    context_model: type[T],
) -> Callable[[Callable[Concatenate[RunContext[T], P], R]], Callable[P, R]]:
    """Inject the active context as a synchronous helper's first argument.

    The expected custom model is checked on each call, accepting subclasses.
    Unavailable context raises RuntimeError; a mismatched model raises TypeError.
    Decoration itself does not require an active pytest session.
    """
    if not isinstance(context_model, type) or not issubclass(context_model, BaseCustomContext):
        raise TypeError("context_model must inherit BaseCustomContext")

    def decorate(function: Callable[Concatenate[RunContext[T], P], R]) -> Callable[P, R]:
        @wraps(function)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            context = get_run_context()
            if not isinstance(context.custom, context_model):
                raise TypeError(
                    f"Expected custom context of type {context_model.__qualname__}, "
                    f"got {type(context.custom).__qualname__}"
                )
            return function(cast("RunContext[T]", context), *args, **kwargs)

        return wrapped

    return decorate
