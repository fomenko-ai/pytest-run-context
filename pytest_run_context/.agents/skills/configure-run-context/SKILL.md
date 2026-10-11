---
name: configure-run-context
description: Configure and extend pytest-run-context in a pytest project. Use when the user asks to define a BaseCustomContext model, call configure(), use the fixture or accessor, persist updates, select a Storage backend, use --run-id, or operate RunContext outside pytest. Do not use primarily for initial installation, reporting, or legacy migration.
---

# Configure run context

Configure project-owned custom metadata while preserving the plugin's lifecycle and storage
contracts.

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

Inspect first, and ask only what cannot be determined reliably from the project. Group a small
number of specific questions when several material choices remain. If ambiguity appears during
implementation, stop changing files, explain it, and request a decision.

## Establish the installed API

Inspect the declared and installed `pytest-run-context` version, imports, root `conftest.py`,
existing context models, storage setup, `--run-id` usage, xdist settings, and external orchestration.
Do not mix APIs from different versions or use private plugin/registry state.

Read [references/custom-context.md](references/custom-context.md) when defining or updating a
schema. Read [references/persistence.md](references/persistence.md) before choosing Storage,
crossing a process boundary, or implementing standalone create/load/finish steps.

## Configure once

For version 0.1.0, configure the already auto-loaded plugin from the project's root hook:

```python
from pytest_run_context import BaseCustomContext, configure
from pytest_run_context.storage import SQLiteStorage


class ProjectContext(BaseCustomContext):
    environment: str = "dev"


def pytest_configure(config) -> None:
    configure(
        config,
        context_model=ProjectContext,
        storage=SQLiteStorage("runs.db"),
    )
```

Adapt paths and fields to established project requirements. Do not introduce example defaults as
real architecture decisions. `configure()` rejects repeated calls and requires a
`BaseCustomContext` subclass plus a `Storage` implementation.

## Use the shared context

Inside tests and fixtures, request the session-scoped `run_context` fixture. Code running within
the active pytest context can call the public `get_run_context()` accessor. These expose the same
instance in one process:

```python
from pytest_run_context import get_run_context


def test_service(run_context) -> None:
    run_context.custom.environment = "staging"
    assert get_run_context() is run_context
    run_context.save()
```

Assignment is validated by Pydantic. An in-memory mutation is immediately visible through that
same instance, but `save()` is required when the snapshot must be persisted. Do not mutate
`RunInfo`; it is immutable and plugin-owned.

## Implement minimally and verify

Preserve existing hooks and dependency conventions. Never put credentials, tokens, or passwords
in model fields, source files, sample data, or logs. Verify model validation, fixture/accessor
identity, explicit persistence, lifecycle ownership, and backend cleanup with the project's
narrowest relevant tests. For xdist, verify behavior with the selected shared backend and account
for complete-snapshot last-write-wins semantics.

Report the schema ownership, persistence points, lifecycle owner, concurrency limits, and checks
actually run.
