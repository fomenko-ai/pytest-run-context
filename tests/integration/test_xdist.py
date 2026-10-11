from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

from pydantic import Field

from pytest_run_context import BaseCustomContext, RunContext, RunInfo
from pytest_run_context.storage import SQLiteStorage


class XdistContext(BaseCustomContext):
    environment: str = "unprepared"
    start_calls: int = 0
    finish_calls: int = 0
    writers: list[str] = Field(default_factory=list)

    def on_run_start(self, info: RunInfo) -> None:
        self.start_calls += 1

    def on_run_finish(self, info: RunInfo) -> None:
        self.finish_calls += 1


def _write_project(
    project: Path, database: Path, events: Path, *, save_changes: bool = True
) -> None:
    project.mkdir()
    (project / "conftest.py").write_text(
        textwrap.dedent(
            f"""
            import json
            import os
            from pathlib import Path

            from pydantic import Field

            from pytest_run_context import BaseCustomContext, configure
            from pytest_run_context.storage import SQLiteStorage

            EVENTS = Path({str(events)!r})

            def record(event, run_id):
                payload = json.dumps({{
                    "event": event,
                    "run_id": run_id,
                    "worker": os.environ.get("PYTEST_XDIST_WORKER", "controller"),
                }}) + "\\n"
                descriptor = os.open(EVENTS, os.O_APPEND | os.O_CREAT | os.O_WRONLY)
                try:
                    os.write(descriptor, payload.encode())
                finally:
                    os.close(descriptor)

            class ProjectContext(BaseCustomContext):
                environment: str = "unprepared"
                start_calls: int = 0
                finish_calls: int = 0
                writers: list[str] = Field(default_factory=list)

                def on_run_start(self, info):
                    self.start_calls += 1
                    record("start", info.run_id)

                def on_run_finish(self, info):
                    self.finish_calls += 1
                    record("finish", info.run_id)

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
    (project / "test_workers.py").write_text(
        textwrap.dedent(
            f"""
            import json
            import os
            import time

            import pytest

            from pytest_run_context import get_run_context

            EVENTS = {str(events)!r}
            SAVE_CHANGES = {save_changes!r}

            def record(event, run_id, worker):
                payload = json.dumps({{
                    "event": event,
                    "run_id": run_id,
                    "worker": worker,
                }}) + "\\n"
                descriptor = os.open(EVENTS, os.O_APPEND | os.O_CREAT | os.O_WRONLY)
                try:
                    os.write(descriptor, payload.encode())
                finally:
                    os.close(descriptor)

            @pytest.mark.parametrize("case", range(16))
            def test_context_on_worker(case, run_context):
                worker = os.environ["PYTEST_XDIST_WORKER"]
                assert run_context is get_run_context()
                assert run_context.custom.environment in {{"unprepared", "prepared"}}
                record("test", run_context.info.run_id, worker)
                if run_context.custom.environment == "prepared":
                    if worker not in run_context.custom.writers:
                        run_context.custom.writers.append(worker)
                    if SAVE_CHANGES:
                        run_context.save()
                elif worker not in run_context.custom.writers:
                    run_context.custom.writers.append(worker)
                    run_context.save()
                time.sleep(0.02)
            """
        ),
        encoding="utf-8",
    )


def _run_xdist(project: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    # The command uses the current interpreter and caller-controlled test arguments.
    return subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "pytest",
            "--strict-markers",
            "-n",
            "4",
            *arguments,
            str(project),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def _read_events(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_xdist_workers_load_one_externally_owned_run(tmp_path: Path) -> None:
    database = tmp_path / "runs.db"
    events = tmp_path / "events.jsonl"
    project = tmp_path / "project"
    storage = SQLiteStorage(database)
    context = RunContext.create(
        context_model=XdistContext,
        storage=storage,
        run_id="prepared-run",
    )
    context.custom.environment = "prepared"
    context.save()
    storage.close()
    _write_project(project, database, events)

    result = _run_xdist(project, "--run-id=prepared-run")

    assert result.returncode == 0, result.stdout + result.stderr
    recorded = _read_events(events)
    test_events = [event for event in recorded if event["event"] == "test"]
    assert {event["worker"] for event in test_events} == {
        "gw0",
        "gw1",
        "gw2",
        "gw3",
    }
    assert {event["run_id"] for event in test_events} == {"prepared-run"}
    assert not [event for event in recorded if event["event"] in {"start", "finish"}]

    verification_storage = SQLiteStorage(database)
    restored = RunContext.load(
        run_id="prepared-run",
        context_model=XdistContext,
        storage=verification_storage,
    )
    assert restored.custom.environment == "prepared"
    assert restored.custom.start_calls == 1
    assert restored.custom.finish_calls == 0
    assert restored.info.finished_at is None
    assert len(restored.custom.writers) == 1
    assert restored.custom.writers[0] in {"gw0", "gw1", "gw2", "gw3"}

    restored.finish()
    assert restored.info.finished_at is not None
    assert restored.custom.finish_calls == 1
    verification_storage.close()

    final_storage = SQLiteStorage(database)
    final = RunContext.load(
        run_id="prepared-run",
        context_model=XdistContext,
        storage=final_storage,
    )
    assert final.info.finished_at is not None
    assert final.custom.finish_calls == 1
    final_storage.close()


def test_xdist_external_run_does_not_save_implicit_worker_changes(
    tmp_path: Path,
) -> None:
    database = tmp_path / "runs.db"
    events = tmp_path / "events.jsonl"
    project = tmp_path / "project"
    storage = SQLiteStorage(database)
    context = RunContext.create(
        context_model=XdistContext,
        storage=storage,
        run_id="prepared-run",
    )
    context.custom.environment = "prepared"
    context.save()
    storage.close()
    _write_project(project, database, events, save_changes=False)

    result = _run_xdist(project, "--run-id=prepared-run")

    assert result.returncode == 0, result.stdout + result.stderr
    verification_storage = SQLiteStorage(database)
    restored = RunContext.load(
        run_id="prepared-run",
        context_model=XdistContext,
        storage=verification_storage,
    )
    assert restored.custom.writers == []
    assert restored.info.finished_at is None
    verification_storage.close()


def test_xdist_without_run_id_creates_and_finishes_one_context(
    tmp_path: Path,
) -> None:
    database = tmp_path / "runs.db"
    events = tmp_path / "events.jsonl"
    project = tmp_path / "project"
    _write_project(project, database, events)

    result = _run_xdist(project)

    assert result.returncode == 0, result.stdout + result.stderr
    recorded = _read_events(events)
    test_events = [event for event in recorded if event["event"] == "test"]
    assert {event["worker"] for event in test_events} == {
        "gw0",
        "gw1",
        "gw2",
        "gw3",
    }
    worker_run_ids = {event["run_id"] for event in test_events}
    assert len(worker_run_ids) == 1

    start_events = [event for event in recorded if event["event"] == "start"]
    finish_events = [event for event in recorded if event["event"] == "finish"]
    assert len(start_events) == 1
    assert len(finish_events) == 1
    assert {event["run_id"] for event in start_events} == {
        event["run_id"] for event in finish_events
    }
    assert {event["worker"] for event in start_events} == {"controller"}

    connection = sqlite3.connect(database)
    try:
        rows = connection.execute("SELECT info, custom FROM runs").fetchall()
    finally:
        connection.close()
    assert len(rows) == 1
    assert all(json.loads(info)["finished_at"] is not None for info, _ in rows)
    assert all(json.loads(custom)["start_calls"] == 1 for _, custom in rows)
    assert all(json.loads(custom)["finish_calls"] == 1 for _, custom in rows)
    saved_custom = json.loads(rows[0][1])
    assert len(saved_custom["writers"]) == 1
    assert saved_custom["writers"][0] in {"gw0", "gw1", "gw2", "gw3"}


def test_xdist_rejects_memory_storage(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "test_example.py").write_text(
        "def test_example(run_context): pass\n",
        encoding="utf-8",
    )

    result = _run_xdist(project)

    assert result.returncode != 0
    assert "MemoryStorage cannot be used with multiple processes" in (result.stdout + result.stderr)


def test_ordinary_pytest_works_without_xdist_plugin(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "test_example.py").write_text(
        "def test_example(run_context): assert run_context.info.run_id\n",
        encoding="utf-8",
    )

    # The command uses the current interpreter and a test-generated project path.
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "pytest",
            "--strict-markers",
            "-p",
            "no:xdist",
            str(project),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
