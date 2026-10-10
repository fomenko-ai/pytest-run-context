#!/usr/bin/env sh

set -eu

for python_version in 3.9 3.10 3.11 3.12 3.13 3.14; do
    echo "Running tests on Python ${python_version} with latest compatible dependencies"
    uv run \
        --isolated \
        --no-project \
        --python "${python_version}" \
        --with-editable ".[dev]" \
        pytest tests
done

for python_version in 3.9 3.10 3.11; do
    echo "Running tests on Python ${python_version} with minimum supported dependencies"
    uv run \
        --isolated \
        --no-project \
        --python "${python_version}" \
        --with-editable ".[dev]" \
        --with "pydantic==2.0" \
        --with "pytest==7.0.0" \
        pytest tests
done
