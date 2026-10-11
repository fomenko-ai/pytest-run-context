# Storage selection

Confirm constructor signatures and behavior in the installed version before editing a project.

| Backend | Persistence and sharing | Important limits | Typical fit |
| --- | --- | --- | --- |
| `MemoryStorage` | Lives for one Storage instance | Independent processes cannot share it; rejected for xdist | One-process pytest run with no durable history |
| `JSONStorage(directory)` | One durable JSON file per run; no expiry | Intended for sequential, single-process access; not a concurrent coordination backend | Human-readable local snapshots |
| `SQLiteStorage(database)` | Durable database; no expiry; shareable when processes reach the same file | Complete snapshots and no field-level merge; coordinate write-heavy concurrency | Local persistence and modest multiprocess workflows |
| `RedisStorage` | Shared service; TTL renewed on each write | External Redis lifecycle; optional dependency; complete snapshots and last-write-wins | Distributed processes needing shared storage |

Redis defaults to a TTL of 86,400 seconds. `ttl_seconds=0` disables expiry. A negative TTL or retry
count is invalid. `RedisStorage.from_url()` accepts retry configuration and owns the client it
creates; `RedisStorage(client)` does not close an injected client.

All backends atomically reject creation of an existing `run_id`. `save()` and `finish()` update an
existing run rather than creating one. Storage receives `RunInfo` and custom context as separate
JSON strings and must remain independent of project-specific Pydantic models.

Storage passed to standalone `RunContext.create()` or `load()` remains caller-owned. Close it with
`try/finally`. The pytest adapter closes the Storage configured for its session.

Never commit credentials. Obtain Redis passwords and similar values through the target project's
existing secret-management mechanism, and do not log connection URLs containing secrets.
