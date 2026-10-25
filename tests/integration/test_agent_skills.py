from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from tarfile import open as tar_open
from zipfile import ZipFile

import pytest

PROJECT_ROOT = Path(__file__).parents[2]
EXPECTED_SKILLS = {
    "configure-run-context",
    "integrate-run-context-reporting",
    "migrate-to-pytest-run-context",
    "setup-pytest-run-context",
    "refactor-to-with-run-context",
}


def run_command(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - arguments are fixed by these repository tests
        args,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def build_distributions(output_directory: Path) -> tuple[Path, Path]:
    run_command("uv", "build", "--out-dir", str(output_directory), cwd=PROJECT_ROOT)
    wheel = next(output_directory.glob("*.whl"))
    sdist = next(output_directory.glob("*.tar.gz"))
    return wheel, sdist


def skill_names(paths: list[str]) -> set[str]:
    marker = "/.agents/skills/"
    return {
        remainder.split("/", maxsplit=1)[0]
        for path in paths
        if marker in path
        for remainder in [path.split(marker, maxsplit=1)[1]]
    }


@pytest.mark.integration
def test_built_wheel_and_sdist_include_all_skills(tmp_path: Path) -> None:
    wheel, sdist = build_distributions(tmp_path)

    with ZipFile(wheel) as archive:
        wheel_skills = skill_names(archive.namelist())
    with tar_open(sdist) as archive:
        sdist_skills = skill_names(archive.getnames())

    assert wheel_skills == EXPECTED_SKILLS
    assert sdist_skills == EXPECTED_SKILLS


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("PYTEST_RUN_LIBRARY_SKILLS") != "1",
    reason="set PYTEST_RUN_LIBRARY_SKILLS=1 to run the networked library-skills installation test",
)
def test_library_skills_discovers_and_installs_from_wheel(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    wheel, _ = build_distributions(artifacts)
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    (consumer / "pyproject.toml").write_text(
        "[project]\n"
        'name = "skill-consumer"\n'
        'version = "0.0.0"\n'
        'requires-python = ">=3.9"\n'
        f'dependencies = ["pytest-run-context @ {wheel.as_uri()}"]\n',
        encoding="utf-8",
    )

    run_command("uv", "sync", cwd=consumer)
    scan = run_command("uvx", "library-skills", "scan", "--json", cwd=consumer)
    discovered = json.loads(scan.stdout)
    discovered_names = {skill["name"] for skill in discovered["skills"]}
    assert discovered_names >= EXPECTED_SKILLS

    run_command("uvx", "library-skills", "install", "--all", "--yes", cwd=consumer)
    installed_root = consumer / ".agents" / "skills"
    assert {path.name for path in installed_root.iterdir()} == EXPECTED_SKILLS
    run_command("uvx", "library-skills", "--check", cwd=consumer)
