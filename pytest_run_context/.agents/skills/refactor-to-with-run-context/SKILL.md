---
name: refactor-to-with-run-context
description: Refactor existing pytest-run-context helper functions to with_run_context(ProjectContext) with typed model access and fewer redundant context checks. Use for synchronous helpers called during active pytest sessions, including from conftest.py. Keep tests on fixtures and standalone workflows on explicit contexts.
---

# Refactor helpers to with_run_context

Replace repeated active-context lookup and equivalent model checks with typed injection into
ordinary helper functions. Preserve observable behavior, model validation, and persistence timing.

## Clarification before changes

Before making any changes, analyze the user's request and the existing project configuration.

If the available information is insufficient to determine the intended behavior, configuration,
or implementation approach, you MUST ask the user specific clarifying questions and wait for
their answers.

Do not modify files, dependencies, or configuration until the ambiguity is resolved.

Do not silently assume user preferences, choose between materially different approaches, or
invent missing requirements.

Read-only project inspection is allowed before clarification.

If the request and project context provide sufficient information, proceed without unnecessary
questions.

## Find eligible helpers

Inspect the installed package's public exports: with_run_context is available from version 0.2.0.
Do not silently upgrade an older project or import private registry functions to emulate it.
Find configure(), the real BaseCustomContext subclass, get_run_context() calls, casts, context
type checks, and every caller of a candidate helper. Use the existing model; do not duplicate its
schema or import conftest.py from application modules. If helpers must share a model currently
defined in conftest.py, consider a project-owned model module without introducing import cycles.

Eligible helpers are synchronous functions whose callers require the active pytest context.
Decoration may happen at import time, but invocation must follow activation in pytest_sessionstart()
and precede teardown. pytest_configure() and standalone create/load scripts do not have that active
context. Do not promise propagation to new threads or processes; xdist workers have their own instances.

Keep the run_context fixture in tests. Do not apply with_run_context to tests, pytest fixtures,
hooks, instance methods, or async functions. Fixtures and hooks may call eligible decorated helpers
when context is active. Do not replace a reusable function's explicit context parameter if callers
also use it with standalone contexts or intentionally pass a different context.

## Refactor the helper and its callers

Use @with_run_context(ProjectContext) and a first parameter annotated RunContext[ProjectContext].
The decorator injects the same active instance, verifies custom with isinstance (including
subclasses), and preserves static types of remaining arguments and the return value.

For an existing ProjectContext with an environment field, before:

```python
from pytest_run_context import get_run_context


def set_environment(environment: str) -> None:
    context = get_run_context()
    if context is None:
        raise RuntimeError("Missing context")
    if not isinstance(context.custom, ProjectContext):
        raise TypeError("Unexpected custom model")
    context.custom.environment = environment
    context.save()
```

After, using the same project model import:

```python
from pytest_run_context import RunContext, with_run_context


@with_run_context(ProjectContext)
def set_environment(context: RunContext[ProjectContext], environment: str) -> None:
    context.custom.environment = environment
    context.save()
```

The call remains set_environment("stage"). A fixture in conftest.py can call the helper normally;
the fixture itself is not decorated with with_run_context. For migrated helpers that previously
accepted an explicit context, remove that argument at every eligible call site, including keyword
calls and partial applications. Keep other parameters, defaults, return values, and exceptions.

Remove context-is-None checks only where the accessor already returned a context or raised. Remove
casts and custom-model isinstance checks only where the decorator supplies the same guarantee.
An exact type(...) is ProjectContext check is stricter than isinstance and is not interchangeable.
If callers rely on a particular error message or exception behavior, retain that contract or surface
the difference before changing it. Keep runtime checks that validate a stronger model subtype.

Access typed fields directly through context.custom or a local reference to that same model.
Do not introduce model_dump(), dictionary lookups, unchecked model construction, or copies to work
around types. Keep checks for optional fields, required business state, and unavailable external
resources. Do not remove intentional no-context fallbacks: the decorator raises before the body runs.
Do not add or move save(), create(), finish(), or lifecycle callbacks as part of this refactor.

## Verify the migration

Run the project's type checker on the helper and callers: callers omit the injected argument and
incorrect remaining arguments should still fail. Exercise fixture-to-helper calls, context identity,
wrong-model rejection, and unavailable-context behavior with isolated pytest runs or existing fakes.
Verify any preserved field checks and explicit persistence boundaries. Follow local rules for test
changes, then run relevant project checks. Report migrated helpers, retained checks, and any helpers
left explicit because their lifecycle or caller requirements differ.
