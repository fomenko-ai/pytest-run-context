import subprocess

import pytest

PYTHON_VERSIONS = ("3.9", "3.10", "3.11", "3.12", "3.13", "3.14")
MINIMUM_DEPENDENCY_PYTHON_VERSIONS = ("3.9", "3.10", "3.11")
MINIMUM_DEPENDENCIES = (
    "pydantic==2.0",
    "pytest==7.0.0",
)


def run_tests(
    python_version: str, *dependencies: str
) -> subprocess.CompletedProcess[str]:
    command = [
        "uv",
        "run",
        "--isolated",
        "--no-project",
        "--python",
        python_version,
        "--with-editable",
        ".[dev]",
    ]
    for dependency in dependencies:
        command.extend(("--with", dependency))
    command.extend(("pytest", "tests/unit"))

    return subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
    )


def assert_tests_passed(
    result: subprocess.CompletedProcess[str],
    python_version: str,
    dependency_set: str,
) -> None:
    assert result.returncode == 0, (
        f"Tests failed on Python {python_version} with {dependency_set}\n\n"
        f"stdout:\n{result.stdout}\n\n"
        f"stderr:\n{result.stderr}"
    )


@pytest.mark.parametrize("python_version", PYTHON_VERSIONS)
def test_project_on_python_version(python_version: str) -> None:
    result = run_tests(python_version)

    assert_tests_passed(result, python_version, "latest compatible dependencies")


@pytest.mark.parametrize("python_version", MINIMUM_DEPENDENCY_PYTHON_VERSIONS)
def test_project_with_minimum_dependencies(python_version: str) -> None:
    result = run_tests(python_version, *MINIMUM_DEPENDENCIES)

    assert_tests_passed(result, python_version, "minimum supported dependencies")
