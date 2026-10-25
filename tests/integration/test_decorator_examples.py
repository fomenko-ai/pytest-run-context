from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from shutil import copytree, ignore_patterns

import pytest

pytest_plugins = ["pytester"]
pytestmark = pytest.mark.integration
EXAMPLES_ROOT = Path(__file__).parents[2] / "examples"


@pytest.mark.parametrize(
    "example",
    [
        "memory_storage",
        "json_storage",
        "sqlite_storage",
        "redis_storage",
        "standalone",
        "external_preparation",
    ],
)
def test_conftest_helpers_in_examples(
    example: str,
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    copytree(
        EXAMPLES_ROOT / example,
        pytester.path,
        dirs_exist_ok=True,
        ignore=ignore_patterns("__pycache__"),
    )
    monkeypatch.setenv("PYTEST_RUN_CONTEXT_JSON_DIRECTORY", str(pytester.path / "runs"))
    monkeypatch.setenv("PYTEST_RUN_CONTEXT_SQLITE_PATH", str(pytester.path / "runs.db"))
    monkeypatch.setenv("PYTEST_RUN_CONTEXT_EXTERNAL_DB", str(pytester.path / "external.db"))

    if example == "redis_storage":
        conftest = pytester.path / "conftest.py"
        conftest.write_text(
            conftest.read_text(encoding="utf-8")
            + """
from unittest.mock import patch
from pytest_run_context.storage import MemoryStorage

# Exercise the example's helper without an external Redis service.
_redis_patch = patch.object(RedisStorage, "from_url", return_value=MemoryStorage())
_redis_patch.start()

def pytest_unconfigure(config: pytest.Config) -> None:
    _redis_patch.stop()
""",
            encoding="utf-8",
        )

    expected_field = "environment" if example == "external_preparation" else "message"
    expected_value = "prepared" if example == "external_preparation" else "prepared in conftest"
    pytester.makepyfile(
        test_00_preparation=f"""
        from pytest_run_context import RunContext, get_run_context

        def test_prepared_by_session_fixture(run_context: RunContext) -> None:
            assert run_context is get_run_context()
            assert run_context.custom.{expected_field} == {expected_value!r}
        """
    )

    if example != "external_preparation":
        result = pytester.runpytest_subprocess("--strict-markers")
        result.assert_outcomes(passed=2)
        return

    # Commands execute only repository-owned scripts copied into this isolated directory.
    preparation = subprocess.run(  # noqa: S603
        [sys.executable, str(pytester.path / "prepare.py")],
        cwd=pytester.path,
        check=True,
        capture_output=True,
        text=True,
    )
    run_id = preparation.stdout.strip()
    try:
        result = pytester.runpytest_subprocess("--strict-markers", f"--run-id={run_id}")
        result.assert_outcomes(passed=2)
    finally:
        subprocess.run(  # noqa: S603
            [sys.executable, str(pytester.path / "cleanup.py"), run_id],
            cwd=pytester.path,
            check=True,
            capture_output=True,
            text=True,
        )
