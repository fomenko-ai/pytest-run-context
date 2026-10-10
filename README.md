
<p align="center">
  <img src="logo.png" alt="pytest-run-context logo" width="720">
</p>

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pytest-run-context.svg)](https://pypi.org/project/pytest-run-context/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

# pytest-run-context

Minimal pytest plugin: one mutable, session-wide Pydantic context, explicit persistence and pluggable Storage.

## Usage

`conftest.py`:

```python
from typing import Optional

from pydantic import Field
from pytest_run_context import BaseCustomContext, configure
from pytest_run_context.storage import SQLiteStorage


class ProjectContext(BaseCustomContext):
    environment: str = "dev"
    stand_id: Optional[str] = None
    service_versions: dict[str, str] = Field(default_factory=dict)


def pytest_configure(config):
    configure(config, context_model=ProjectContext, storage=SQLiteStorage("runs.db"))
```

`tests/test_example.py`:

```python
from pytest_run_context import get_run_context


def test_context(run_context):
    run_context.custom.stand_id = "stand-01"
    assert get_run_context() is run_context
    run_context.save()
```

`--run-id` can override the generated UUID; existing IDs cannot be reused.
Without `configure()`, the plugin uses in-memory storage and the base custom
context. Custom data is saved explicitly, plus automatic writes at session
start and finish. The plugin does not collect test results. SQLite and JSON
data never expire automatically; Redis TTL is configurable and renewed on
every write. JSON storage is intended for sequential, single-process usage.
`get_run_context()` uses `ContextVar`; new threads do not inherit it
automatically.

## Development with uv

The repository pins Python 3.14 for local development in `.python-version`.
Install the locked default development environment:

```bash
uv sync --locked
```

Tests are separated by purpose:

```text
tests/
├── unit/           # isolated tests using in-memory objects and fakes
└── integration/    # persistent file backends and real Redis
```

Plain pytest runs only unit tests because `tests/unit` is configured as the
default `testpaths` value:

```bash
uv run pytest --strict-markers
```

File-backed SQLite and JSON integration tests use temporary directories and do
not require external services:

```bash
uv run pytest --strict-markers tests/integration/test_file_storage.py
```

Redis integration tests use a disposable `redis:7.4-alpine` Testcontainers
instance and require a running Docker daemon. Install their non-default
development dependency group and run the integration directory explicitly:

```bash
uv sync --locked --group redis-integration
uv run --group redis-integration pytest --strict-markers tests/integration
```

Run the complete quality sequence (unit tests, integration tests, Python
compatibility tests, Ruff lint and format checks, then ty):

```bash
./scripts/ci.sh
```

The complete script requires Docker and network access for the Redis container
image and isolated compatibility environments.

For individual checks:

```bash
uv run pytest --strict-markers python_compatibility_tests
uv run ruff check .
uv run ruff format --check .
uv run ty check
```

To install the plugin in another uv project:

```bash
uv add --editable /path/to/pytest-run-context
# with optional Redis support: uv add 'pytest-run-context[redis]'
```

`uv.lock` pins dependency versions when they can be resolved through the package index. After changing dependencies, run `uv lock` and commit the file. Once installed, the plugin is loaded automatically through the `pytest11` entry point.

## Examples

Runnable pytest projects for Memory, JSON, SQLite, and Redis storage are in
[`examples/`](examples/README.md). Each backend has an independent `conftest.py`
and test module, together with its setup and run command. Configurable examples
use the `PYTEST_RUN_CONTEXT_*` variables listed in [`.env.example`](.env.example).

## Compatibility

The project supports Python 3.9 through 3.14 and pytest 7.0 or newer. The
compatibility suite tests every supported Python version with the latest compatible
dependencies. It also tests the minimum supported Pydantic and pytest versions on
Python 3.9 through 3.11.

Run the compatibility matrix through pytest:

```bash
uv run pytest --strict-markers python_compatibility_tests -v
```

Or run the standalone shell script:

```bash
./python_compatibility_tests/run_python_compatibility.sh
```
