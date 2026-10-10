# Standalone pytest execution

This example lets pytest create and own a context. At session start the plugin
calls `RunContext.create()`. At session completion it calls `finish()`, which
runs `on_run_finish()` and persists the final state.

Run from the repository root:

```bash
uv run pytest --strict-markers examples/standalone
```

`MemoryStorage` is sufficient because context creation and use happen in one
process. Do not pass `--run-id`: that option loads an existing context.
