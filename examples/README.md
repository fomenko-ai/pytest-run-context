# Storage examples

Each directory is a self-contained pytest project showing how to configure one
of the storage implementations bundled with `pytest-run-context`. Run commands
from the repository root. Ordinary standalone runs do not pass `--run-id`;
pytest creates a generated ID. Passing `--run-id` always means loading an
existing run rather than choosing an ID for a new run.

All examples demonstrate the same lifecycle:

1. pytest loads the plugin automatically through its `pytest11` entry point;
2. the example's `conftest.py` supplies a custom Pydantic model and storage;
3. the test updates the shared context and explicitly saves a snapshot;
4. the plugin finishes contexts that pytest created itself.

Two workflow-focused examples are also available:

- [`standalone/`](standalone/README.md) shows pytest creating and finishing an
  in-memory context;
- [`external_preparation/`](external_preparation/README.md) shows preparation,
  pytest, and cleanup sharing a persistent SQLite context across processes.

## Environment configuration

JSON, SQLite, and Redis examples load the root `.env` file with
`python-dotenv`. Install the examples dependency group and copy the safe
template before changing values locally:

```bash
uv sync --locked --group examples
cp .env.example .env
```

The `.env` file is ignored by Git. Keep real Redis credentials only in that
local file; never add them to `.env.example`. All example settings use the
`PYTEST_RUN_CONTEXT_` prefix. Environment variables already exported by the
shell take precedence over values in `.env`.

## Memory storage

Memory storage needs no external resources and retains data only for the
lifetime of its storage instance:

```bash
uv run pytest --strict-markers examples/memory_storage
```

## JSON storage

JSON storage creates one JSON file per run. By default, the example writes to
`/tmp/pytest-run-context-example/json`. Override the directory with
`PYTEST_RUN_CONTEXT_JSON_DIRECTORY`:

```bash
PYTEST_RUN_CONTEXT_JSON_DIRECTORY=/tmp/my-run-context-json \
uv run --group examples pytest --strict-markers examples/json_storage
```

The filename is a SHA-256 hash of the run ID. The JSON document contains the
run ID plus the separately serialized `RunInfo` and custom context.

## SQLite storage

SQLite storage writes to `/tmp/pytest-run-context-example/runs.sqlite3` by
default. Override the database path with `PYTEST_RUN_CONTEXT_SQLITE_PATH`:

```bash
PYTEST_RUN_CONTEXT_SQLITE_PATH=/tmp/my-run-context.sqlite3 \
uv run --group examples pytest --strict-markers examples/sqlite_storage
```

## Redis storage

Install the optional Redis dependency and start Redis separately. The plugin
does not create or manage a Redis server:

```bash
uv sync --locked --group examples --extra redis
uv run --group examples --extra redis pytest --strict-markers examples/redis_storage
```

Redis connection settings are split across
`PYTEST_RUN_CONTEXT_REDIS_URL`, `PYTEST_RUN_CONTEXT_REDIS_PORT`,
`PYTEST_RUN_CONTEXT_REDIS_DB`, `PYTEST_RUN_CONTEXT_REDIS_USERNAME`, and
`PYTEST_RUN_CONTEXT_REDIS_PASSWORD`. TTL defaults to `86400` seconds and can be
disabled with `PYTEST_RUN_CONTEXT_REDIS_TTL=0`.

Connection retries use redis-py's exponential backoff. Configure them with
`PYTEST_RUN_CONTEXT_REDIS_RETRIES`, `PYTEST_RUN_CONTEXT_REDIS_BACKOFF_BASE`,
and `PYTEST_RUN_CONTEXT_REDIS_BACKOFF_CAP`; their defaults are documented in
`.env.example`.

Run each storage directory in a separate pytest invocation. A pytest session
can configure the plugin only once, so collecting multiple example directories
together would attempt to configure several storage backends for one session.

Delete files under `/tmp/pytest-run-context-example` when you no longer need
the persistent example data.
