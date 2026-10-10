#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

uv sync --locked --group redis-integration

echo "Running unit tests"
uv run pytest --strict-markers tests/unit

echo "Running integration tests"
uv run --group redis-integration pytest --strict-markers tests/integration

echo "Running Python compatibility tests"
uv run pytest --strict-markers python_compatibility_tests

echo "Running Ruff lint checks"
uv run ruff check .

echo "Running Ruff format checks"
uv run ruff format --check .

echo "Running ty checks"
uv run ty check
