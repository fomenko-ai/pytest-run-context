# Contributing

## Setup

The project uses Python 3.14 for local development and `uv` for dependency
management. Install the locked default development environment:

```bash
uv sync --locked
```

To run Redis integration tests, install the non-default Testcontainers group as
well. A running Docker daemon is required:

```bash
uv sync --locked --group redis-integration
```

## Test Layout

- `tests/unit/` contains isolated unit tests and is the default pytest path.
- `tests/integration/` contains SQLite, JSON, and Redis backend integration
  tests.
- `python_compatibility_tests/` runs the unit suite across supported Python and
  dependency versions.

Run unit tests:

```bash
uv run pytest --strict-markers
```

Run file-backed integration tests without Docker:

```bash
uv run pytest --strict-markers tests/integration/test_file_storage.py
```

Run all integration tests, including Redis through Testcontainers:

```bash
uv run --group redis-integration pytest --strict-markers tests/integration
```

Run the Python compatibility matrix:

```bash
uv run pytest --strict-markers python_compatibility_tests
```

## Complete Quality Check

The project script runs unit tests, integration tests, compatibility tests,
Ruff linting, Ruff formatting, and ty type checking in that order. It stops at
the first failure:

```bash
./scripts/ci.sh
```

The script requires Docker and network access.

## Individual Static Checks

Run Ruff linting and formatting checks:

```bash
uv run ruff check .
uv run ruff format --check .
```

Run static type checking:

```bash
uv run ty check
```
