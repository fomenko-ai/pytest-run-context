# Standalone pytest execution

This example focuses on lifecycle ownership when pytest is the only
orchestrator. The plugin creates the context at session start and finishes it
at session completion.

## Context flow

```mermaid
flowchart TD
    A[pytest starts] --> B[conftest.py configures the loaded plugin]
    B --> C[plugin creates RunContext]
    C --> D[on_run_start runs once]
    D --> E[plugin saves initial state]
    E --> P[session fixture calls decorated prepare_context]
    P --> F[test receives run_context]
    F --> G[get_run_context returns the same instance]
    G --> H[test changes custom data and calls save]
    H --> I[pytest session completes]
    I --> J[plugin calls finish]
    J --> K[on_run_finish runs once]
    K --> L[plugin saves final state and closes storage]
```

`MemoryStorage` is enough here because every lifecycle stage happens in one
process. The focus is not durable persistence, but which component owns
creation and finalization.

## Run the example

From the repository root:

```bash
uv sync --locked
uv run pytest --strict-markers examples/standalone
```

Do not pass `--run-id`. That option means loading an existing context, whereas
this workflow intentionally lets pytest create a new one.
