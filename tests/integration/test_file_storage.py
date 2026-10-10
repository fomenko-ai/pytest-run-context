from __future__ import annotations

import subprocess
import sys
import textwrap
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from pytest_run_context import BaseCustomContext, RunContext
from pytest_run_context.storage import (
    JSONStorage,
    RunAlreadyExistsError,
    SQLiteStorage,
    Storage,
    StoredRun,
)

pytestmark = pytest.mark.integration

StorageFactory = Callable[[Path], Storage]


class CrossProcessContext(BaseCustomContext):
    environment: str = "unprepared"
    observed_by_pytest: bool = False


@pytest.fixture(params=["sqlite", "json"])
def storage(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[Storage]:
    factories: dict[str, StorageFactory] = {
        "sqlite": lambda path: SQLiteStorage(path / "runs.db"),
        "json": lambda path: JSONStorage(path / "json"),
    }
    instance = factories[request.param](tmp_path)
    yield instance
    instance.close()


def test_file_storage_contract(storage: Storage) -> None:
    assert storage.load_run("missing") is None
    storage.create_run("r1", "{}", '{"a":1}')
    assert storage.load_run("r1") == StoredRun("{}", '{"a":1}')

    with pytest.raises(RunAlreadyExistsError, match="r1"):
        storage.create_run("r1", "{}", "{}")

    storage.save_run("r1", '{"a":2}', '{"b":3}')
    assert storage.load_run("r1") == StoredRun('{"a":2}', '{"b":3}')

    storage.finish_run("r1", '{"done":true}', "{}")
    assert storage.load_run("r1") == StoredRun('{"done":true}', "{}")


def test_file_storage_rejects_update_for_missing_run(storage: Storage) -> None:
    with pytest.raises(KeyError, match="missing"):
        storage.save_run("missing", "{}", "{}")

    with pytest.raises(KeyError, match="missing"):
        storage.finish_run("missing", "{}", "{}")


def test_json_storage_uses_safe_stable_filename(tmp_path: Path) -> None:
    storage = JSONStorage(tmp_path)

    first = storage._path("../unsafe/id")
    second = storage._path("../unsafe/id")

    assert first == second
    assert first.parent == tmp_path
    assert first.name.endswith(".json")
    assert "unsafe" not in first.name


def test_json_storage_removes_temporary_file_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = JSONStorage(tmp_path)
    storage.create_run("r1", "{}", "{}")

    def fail_replace(source: str, destination: Path) -> None:
        raise OSError(f"cannot replace {destination.name}")

    monkeypatch.setattr("pytest_run_context.storage.json_file.os.replace", fail_replace)

    with pytest.raises(OSError, match="cannot replace"):
        storage.save_run("r1", '{"changed":true}', "{}")

    assert list(tmp_path.iterdir()) == [storage._path("r1")]


def test_sqlite_storage_persists_across_instances(tmp_path: Path) -> None:
    database = tmp_path / "runs.db"
    first = SQLiteStorage(database)
    first.create_run("r1", "info", "custom")
    first.close()

    second = SQLiteStorage(database)
    try:
        assert second.load_run("r1") == StoredRun("info", "custom")
    finally:
        second.close()


def test_sqlite_context_created_outside_pytest_is_loaded_in_subprocess(
    tmp_path: Path,
) -> None:
    database = tmp_path / "runs.db"
    storage = SQLiteStorage(database)
    context = RunContext.create(
        context_model=CrossProcessContext,
        storage=storage,
        run_id="prepared-run",
    )
    context.custom.environment = "prepared"
    context.save()
    storage.close()

    project = tmp_path / "project"
    project.mkdir()
    (project / "conftest.py").write_text(
        textwrap.dedent(
            f"""
            from pytest_run_context import BaseCustomContext, configure
            from pytest_run_context.storage import SQLiteStorage

            class ProjectContext(BaseCustomContext):
                environment: str = "unprepared"
                observed_by_pytest: bool = False

            def pytest_configure(config):
                configure(
                    config,
                    context_model=ProjectContext,
                    storage=SQLiteStorage({str(database)!r}),
                )
            """
        ),
        encoding="utf-8",
    )
    (project / "test_prepared.py").write_text(
        textwrap.dedent(
            """
            from pytest_run_context import get_run_context

            def test_prepared_context(run_context):
                assert run_context is get_run_context()
                assert run_context.custom.environment == "prepared"
                run_context.custom.observed_by_pytest = True
                run_context.save()
            """
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--strict-markers",
            "--run-id=prepared-run",
            str(project),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    verification_storage = SQLiteStorage(database)
    try:
        restored = RunContext.load(
            run_id="prepared-run",
            context_model=CrossProcessContext,
            storage=verification_storage,
        )
        assert restored.custom.environment == "prepared"
        assert restored.custom.observed_by_pytest is True
        assert restored.info.finished_at is None
    finally:
        verification_storage.close()
