# Examples

Each example focuses on one decision so that storage behavior and context
ownership can be understood independently:

- [`memory_storage/`](memory_storage/README.md) shows the smallest storage
  setup when context data is needed only inside one process.
- [`json_storage/`](json_storage/README.md) shows human-readable, file-based
  persistence with one JSON document per run.
- [`sqlite_storage/`](sqlite_storage/README.md) shows durable local persistence
  in a single SQLite database.
- [`redis_storage/`](redis_storage/README.md) shows shared persistence with
  configurable expiry and connection retries in an externally managed Redis
  service.
- [`standalone/`](standalone/README.md) focuses on the lifecycle in which pytest
  creates, saves, and finishes the context itself.
- [`external_preparation/`](external_preparation/README.md) shows a multi-process
  workflow in which an external orchestrator owns the context lifecycle while
  pytest loads and updates that context.
