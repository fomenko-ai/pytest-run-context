# Compatibility matrix

Use this as a starting point, not as a substitute for inspecting the legacy implementation and the
installed package version.

| Legacy capability | Version 0.1.0 mapping | Migration note |
| --- | --- | --- |
| Session context fixture | `run_context` | Session-scoped within each pytest process |
| Non-fixture accessor | `get_run_context()` | Active pytest context only; fails before/after it |
| Project metadata model | `BaseCustomContext` subclass | Assignment validation; extra fields forbidden |
| Run ID and timestamps | immutable `RunInfo` | Only `run_id`, `started_at`, `finished_at` |
| Start callback | `on_run_start(info)` | Creation only, before initial persistence |
| Finish callback | `on_run_finish(info)` | Finish only; not transactional with external effects |
| Intermediate persistence | `RunContext.save()` | Explicit full snapshot; no per-test autosave |
| External preparation | `RunContext.create()` | Caller owns Storage and eventual finish |
| Existing run lookup | `RunContext.load()` / pytest `--run-id` | Loading does not create or invoke start callback |
| Duplicate prevention | `Storage.create_run()` | Atomic rejection required by supplied backends |
| In-memory-only state | `MemoryStorage` | One Storage instance; unsuitable for xdist sharing |
| Local readable files | `JSONStorage` | Sequential, single-process intent; no expiry |
| Local database | `SQLiteStorage` | Durable; complete snapshot writes |
| Distributed backend | `RedisStorage` | Optional dependency; write-renewed TTL; external service |
| Worker state merge | No equivalent | Complete snapshots are last-write-wins |
| Automatic thread propagation | No equivalent | New threads do not automatically inherit `ContextVar` |
| Test outcome collection | No equivalent | Retain in reporting/test infrastructure if required |
| Report generation | No equivalent | Bridge allowlisted context via reporter public API |
| Background save/heartbeat | No equivalent | Retain externally only after explicit approval |
| Generic schema migration | No equivalent | Design project-owned data migration when required |

For every project row, add evidence: defining file, call sites, tests, and stored data impact.
Distinguish unsupported behavior from behavior that merely requires an adapter.
