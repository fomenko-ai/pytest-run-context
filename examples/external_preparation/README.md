# External environment preparation

This example shows a context shared across three processes. An external
preparation step creates it, pytest loads and updates it, and an external
cleanup step finishes it. The external workflow, rather than pytest, owns the
context lifecycle.

## Context flow

```mermaid
flowchart TD
    A[prepare.py creates RunContext] --> B[on_run_start runs once]
    B --> C[preparation updates and saves context]
    C --> D[SQLite stores the generated run ID]
    D --> E[pytest loads context with --run-id]
    E --> P[session fixture calls decorated environment check]
    P --> F[test updates context and calls save]
    F --> G[pytest exits without finishing loaded context]
    G --> H[cleanup.py loads the same context]
    H --> I[cleanup.py calls finish]
    I --> J[on_run_finish runs once]
    J --> K[final state is saved to SQLite]
```

Pytest does not automatically save or finish a context loaded with `--run-id`.
The test therefore calls `run_context.save()` explicitly, and `cleanup.py`
performs finalization after all workflow stages.

## Run the example

From the repository root, install the example dependencies:

```bash
uv sync --locked --group examples
```

Then run the complete workflow in the same shell:

```bash
RUN_ID=$(uv run --group examples python examples/external_preparation/prepare.py)
uv run --group examples pytest --strict-markers examples/external_preparation --run-id="$RUN_ID"
uv run --group examples python examples/external_preparation/cleanup.py "$RUN_ID"
```

`prepare.py` prints the generated run ID after saving the prepared environment.
All three commands use the SQLite database at
`/tmp/pytest-run-context-external-preparation.sqlite3` by default. Override it
consistently for every command by exporting a setting first:

```bash
export PYTEST_RUN_CONTEXT_EXTERNAL_DB=/tmp/my-external-run-context.sqlite3
```

Settings also load the repository's optional `.env` file. In a real
orchestrator, invoke cleanup or equivalent finalization from guaranteed cleanup
logic even when pytest exits unsuccessfully.
