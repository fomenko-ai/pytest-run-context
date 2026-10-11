# External environment preparation

This example creates a context before pytest, lets pytest update it without
finishing it, and lets the external owner finish it after cleanup.

Run the complete workflow from the repository root:

```bash
RUN_ID=$(uv run python examples/external_preparation/prepare.py)
uv run pytest --strict-markers examples/external_preparation --run-id="$RUN_ID"
uv run python examples/external_preparation/cleanup.py "$RUN_ID"
```

`prepare.py` prints the generated ID after saving the prepared environment.
The pytest configuration requires that ID and opens the same SQLite database.
The test calls `run_context.save()` explicitly. Pytest does not automatically
save or finish a context loaded with `--run-id`. `cleanup.py` is the lifecycle
owner and calls `finish()` after all workflow stages.

The database defaults to
`/tmp/pytest-run-context-external-preparation.sqlite3`. Override it consistently
for all three commands with `PYTEST_RUN_CONTEXT_EXTERNAL_DB`. Remove the local
database before rerunning with an explicitly reused ID; generated IDs do not
collide in ordinary use.

In a real orchestrator, call `cleanup.py` or equivalent from guaranteed cleanup
logic even when pytest exits unsuccessfully.
