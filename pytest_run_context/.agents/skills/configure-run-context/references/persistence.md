# Persistence and standalone operation

## Snapshot rules

`RunContext.create()` stores an initial snapshot, `save()` stores an explicit intermediate
snapshot, and `finish()` stores a final snapshot after the finish callback. Storage writes contain
the full `RunInfo` and custom model JSON; concurrent field changes are not merged.

Memory storage lasts only as long as its instance. JSON and SQLite do not expire data. JSON is for
sequential single-process use. SQLite can be shared through a common file. Redis is shared,
renews its configurable TTL on writes, and requires the optional Redis dependency and an externally
managed service. Redis TTL `0` means no expiry.

xdist workers use separate context objects and require shared Storage. Explicit concurrent saves
are last-write-wins. Do not use `MemoryStorage` for xdist or claim that custom data is automatically
propagated between processes.

## Standalone lifecycle

Verify these signatures against the installed version:

```python
from pytest_run_context import RunContext
from pytest_run_context.storage import SQLiteStorage

storage = SQLiteStorage("runs.db")
try:
    context = RunContext.create(
        context_model=ProjectContext,
        storage=storage,
    )
    context.custom.environment = "prepared"
    context.save()
    run_id = context.info.run_id
finally:
    storage.close()
```

Run pytest against the same backend with `--run-id=<existing-id>`. That pytest session loads but
does not finish or automatically save the externally owned run. After all stages:

```python
storage = SQLiteStorage("runs.db")
try:
    context = RunContext.load(
        run_id=run_id,
        context_model=ProjectContext,
        storage=storage,
    )
    context.finish()
finally:
    storage.close()
```

An optional explicit `run_id` belongs on `RunContext.create()`, not on pytest's `--run-id` when a
new run is desired. Duplicate creation is rejected atomically. Loading a missing run fails; loading
a finished run is allowed for inspection, but finishing it again fails. Storage passed to these
standalone APIs is caller-owned.

Do not retry `finish()` blindly: hook side effects and storage writes cannot be made exactly-once by
the current protocol.
