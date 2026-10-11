# pytest-xdist investigation

Date: 2026-10-11

This document records the behavior observed before xdist support was implemented. It is retained
as the investigation that motivated
[`0002-xdist-lifecycle-and-explicit-save.md`](decisions/0002-xdist-lifecycle-and-explicit-save.md).
The current supported behavior is documented in the project README.

## Investigation setup

The investigation used temporary pytest projects and an actual subprocess with `pytest -n 4`.
Every process configured its own `SQLiteStorage` instance pointing to one database. Append-only
diagnostic events identified the xdist controller and workers `gw0` through `gw3`.

The same command now runs regression coverage for the implemented behavior:

```bash
uv run pytest --strict-markers tests/integration/test_xdist.py
```

## Historical behavior before xdist support

### Externally created run with `--run-id`

`RunContext.create()` creates one row before pytest starts. The xdist controller and all four
workers independently execute `pytest_sessionstart` and load that row into separate in-memory
`RunContext` instances. All four workers observe the prepared custom values and the same
`run_id`.

Neither the controller nor workers own this lifecycle, so their `pytest_sessionfinish` hooks call
`save()` rather than `finish()`. The stored run remains unfinished after pytest. Loading it and
calling `finish()` in the external process sets `finished_at` and invokes `on_run_finish()` once.

Full-snapshot saves are not merged. In the diagnostic scenario every worker appends its identity
to its local custom model and calls `save()`. The controller later saves its unchanged snapshot,
and the final stored `writers` value is empty. SQLite serializes the individual statements, but
the plugin provides no revision check, compare-and-swap, or merge; the last completed update wins.

### Run without `--run-id`

The xdist controller and every worker independently create and own a context. With four workers,
the observed result is five distinct SQLite rows. `on_run_start()` and `on_run_finish()` each run
five times, once per process-owned context, and all five rows are automatically finished. Tests
execute only in the four worker contexts; the controller's fifth context has no test consumers.

Consequently, running without `--run-id` does not represent one logical run under xdist.

## Contract selected for implementation

The proposed contract is one externally owned `run_id` shared by all workers. Each worker may load
its own in-memory `RunContext`; the project remains responsible for custom mutability and explicit
`save()` calls. Worker changes are not automatically merged. Only the external lifecycle owner
calls `finish()` after pytest and cleanup complete.

## Problems identified by the investigation

- The plugin does not distinguish the xdist controller from workers when initializing or saving.
- Without `--run-id`, every pytest process creates and finishes a separate run.
- With `--run-id`, the controller performs an unnecessary final save from a stale snapshot.
- `save_run()` replaces complete `info` and `custom` JSON values, so concurrent worker saves are
  last-write-wins and can lose changes.
- `finish()` prevents repeat completion only in one in-memory instance. The storage protocol has
  no atomic lifecycle ownership or compare-and-swap operation for competing processes.
- SQLite uses separate default connections and transactions. It provides statement-level database
  coordination, not application-level ownership or merging; lock contention can still surface as
  `sqlite3.OperationalError` under heavier concurrent writes.

## Recommended direction

For the stated contract, require an externally created `run_id` for xdist runs, make controller
and worker roles explicit in the pytest adapter, and prevent the controller from writing a stale
loaded snapshot. Keep completion with the external lifecycle owner. Document full-snapshot,
last-write-wins worker saves unless a separate requirement justifies a versioned/CAS storage
contract. Supporting pytest-owned xdist runs additionally required selecting exactly one creator
and lifecycle owner and distributing its `run_id` to workers. This direction was implemented by
[decision 0002](decisions/0002-xdist-lifecycle-and-explicit-save.md).
