# Lifecycle selection

Verify these rules against the installed package before applying them; they describe
`pytest-run-context` 0.1.0.

## Pytest-owned run

Use this mode when pytest represents the complete logical run.

- Invoke pytest without `--run-id`.
- The plugin creates one context, calls `on_run_start()`, and persists initial state.
- Explicit `context.save()` calls persist intermediate snapshots.
- At session completion, the plugin calls `finish()`, which supplies final `RunInfo` to
  `on_run_finish()` and persists the final state.
- A test failure does not by itself suppress normal finalization. A final persistence failure makes
  the pytest run fail.

## Externally owned run

Use this mode when preparation, pytest, and cleanup are separate stages of one logical run.

- The external owner calls `RunContext.create(...)`, retains the generated `run_id`, and closes its
  Storage resource.
- Pytest configures the same backend and is invoked with `--run-id=<existing-id>`.
- Pytest loads the run. It does not call `on_run_start()`, automatically save at session end, or
  finish it.
- Tests or fixtures call `save()` for snapshots that must cross process boundaries.
- The external owner later calls `RunContext.load(...)` and `finish()`.

`--run-id` never selects an ID for a new pytest-owned context. An unknown or already finished ID is
a pytest usage error.

## Access boundaries

The session-scoped `run_context` fixture and `get_run_context()` return the same in-memory instance
in one active pytest execution context. The accessor fails before initialization and after teardown.
It is backed by `ContextVar`; new threads do not inherit it automatically.

With xdist, controller and workers hold distinct in-memory instances of the same logical run.
Workers load through shared Storage. Their complete snapshot writes are not merged; the last
completed write wins. Do not promise transparent thread or process propagation.

## Failure boundaries

Lifecycle hooks and persistence do not form one transaction. A hook or storage failure can leave
in-memory state, stored state, or external hook effects out of sync. Do not add silent retries or
claim exactly-once completion. Keep lifecycle hooks safe to diagnose and avoid secrets in errors.
