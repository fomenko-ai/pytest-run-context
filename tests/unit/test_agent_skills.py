from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).parents[2] / "pytest_run_context"
SKILLS_ROOT = PACKAGE_ROOT / ".agents" / "skills"
SCENARIOS_PATH = Path(__file__).parents[1] / "agent_skills" / "scenarios.json"
EXPECTED_REFERENCES = {
    "configure-run-context": {"custom-context.md", "persistence.md"},
    "integrate-run-context-reporting": {"reporting-patterns.md"},
    "migrate-to-pytest-run-context": {
        "compatibility-matrix.md",
        "migration-checklist.md",
    },
    "setup-pytest-run-context": {"lifecycle.md", "storage-selection.md"},
}
REQUIRED_CLARIFICATION_RULE = """Before making any changes, analyze the user's request and the \
existing project configuration.

If the available information is insufficient to determine the intended behavior, configuration,
or implementation approach, you MUST ask the user specific clarifying questions and wait for
their answers.

Do not modify files, dependencies, or configuration until the ambiguity is resolved.

Do not silently assume user preferences, choose between materially different approaches, or
invent missing requirements.

Read-only project inspection is allowed before clarification.

If the request and project context provide sufficient information, proceed without unnecessary
questions."""
PUBLIC_API_NAMES = {
    "BaseCustomContext",
    "RunContext",
    "RunInfo",
    "configure",
    "get_run_context",
}
PUBLIC_STORAGE_NAMES = {
    "JSONStorage",
    "MemoryStorage",
    "RedisStorage",
    "SQLiteStorage",
    "Storage",
}


def skill_directories() -> list[Path]:
    return sorted(path for path in SKILLS_ROOT.iterdir() if path.is_dir())


def read_frontmatter(skill_file: Path) -> dict[str, str]:
    text = skill_file.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    frontmatter, separator, _ = text[4:].partition("\n---\n")
    assert separator
    values: dict[str, str] = {}
    for line in frontmatter.splitlines():
        key, separator, value = line.partition(":")
        assert separator, f"Invalid frontmatter line in {skill_file}: {line}"
        values[key.strip()] = value.strip()
    return values


def python_code_blocks(text: str) -> list[str]:
    return re.findall(r"```python\n(.*?)```", text, flags=re.DOTALL)


def imported_names(code: str, module: str) -> set[str]:
    pattern = rf"from {re.escape(module)} import \((.*?)\)|from {re.escape(module)} import ([^\n]+)"
    names: set[str] = set()
    for grouped, single_line in re.findall(pattern, code, flags=re.DOTALL):
        imported = grouped or single_line
        names.update(
            name.strip() for name in imported.replace("\n", " ").split(",") if name.strip()
        )
    return names


def test_expected_skills_and_references_exist() -> None:
    skills = skill_directories()

    assert {path.name for path in skills} == set(EXPECTED_REFERENCES)
    for skill in skills:
        assert (skill / "SKILL.md").is_file()
        assert (skill / "agents" / "openai.yaml").is_file()
        references = {path.name for path in (skill / "references").glob("*.md")}
        assert references == EXPECTED_REFERENCES[skill.name]


@pytest.mark.parametrize("skill", skill_directories(), ids=lambda path: path.name)
def test_frontmatter_name_matches_directory_and_has_description(skill: Path) -> None:
    frontmatter = read_frontmatter(skill / "SKILL.md")

    assert set(frontmatter) == {"name", "description"}
    assert frontmatter["name"] == skill.name
    assert len(frontmatter["description"]) >= 40


@pytest.mark.parametrize("skill", skill_directories(), ids=lambda path: path.name)
def test_skill_contains_required_clarification_rule(skill: Path) -> None:
    skill_text = (skill / "SKILL.md").read_text(encoding="utf-8")

    assert REQUIRED_CLARIFICATION_RULE in skill_text


@pytest.mark.parametrize("skill", skill_directories(), ids=lambda path: path.name)
def test_internal_markdown_links_resolve(skill: Path) -> None:
    for markdown_file in skill.rglob("*.md"):
        text = markdown_file.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
            if "://" in target or target.startswith("#"):
                continue
            assert (markdown_file.parent / target).resolve().is_file(), (
                f"Broken link {target!r} in {markdown_file}"
            )


def test_python_examples_are_syntax_valid_and_use_public_imports() -> None:
    examples_found = 0
    for markdown_file in SKILLS_ROOT.rglob("*.md"):
        text = markdown_file.read_text(encoding="utf-8")
        for index, code in enumerate(python_code_blocks(text), start=1):
            examples_found += 1
            compile(code, f"{markdown_file} example {index}", "exec")
            assert imported_names(code, "pytest_run_context") <= PUBLIC_API_NAMES
            assert imported_names(code, "pytest_run_context.storage") <= PUBLIC_STORAGE_NAMES

    assert examples_found >= 5


def test_behavior_scenarios_cover_every_skill_and_ambiguity() -> None:
    scenarios = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))

    assert {scenario["skill"] for scenario in scenarios} == set(EXPECTED_REFERENCES)
    assert all(scenario["prompt"].strip() for scenario in scenarios)
    assert all(scenario["expected_behavior"].strip() for scenario in scenarios)
    for skill_name in EXPECTED_REFERENCES:
        skill_scenarios = [scenario for scenario in scenarios if scenario["skill"] == skill_name]
        assert any(scenario["ambiguous"] is False for scenario in skill_scenarios)
        assert any(scenario["ambiguous"] is True for scenario in skill_scenarios)


def test_skills_do_not_claim_unsupported_runtime_features() -> None:
    skill_text = "\n".join(
        path.read_text(encoding="utf-8") for path in SKILLS_ROOT.rglob("*.md")
    ).lower()

    assert "has no native reporting integration" in skill_text
    assert "does not collect test outcomes" in skill_text
    assert "last-write-wins" in skill_text
    assert "threads do not inherit it automatically" in skill_text
