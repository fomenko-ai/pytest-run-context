---
name: setup-pytest-run-context
description: Add pytest-run-context to an existing pytest project and establish the smallest working integration. Use when the user asks to install the package, enable its pytest plugin, or choose between pytest-owned and externally owned run lifecycles. Do not use for detailed schema or reporting work after integration already exists.
---

# Set up pytest-run-context

Integrate the version of `pytest-run-context` available to the target project with the smallest
change that satisfies the requested lifecycle.

## Clarification before changes

Before making any changes, analyze the user's request and the existing project configuration.

If the available information is insufficient to determine the intended behavior, configuration,
or implementation approach, you MUST ask the user specific clarifying questions and wait for
their answers.

Do not modify files, dependencies, or configuration until the ambiguity is resolved.

Do not silently assume user preferences, choose between materially different approaches, or
invent missing requirements.

Read-only project inspection is allowed before clarification.

If the request and project context provide sufficient information, proceed without unnecessary
questions.

Inspect first, and ask only what cannot be determined reliably from the project. Group a small
number of specific questions when several material choices remain. If ambiguity appears during
implementation, stop changing files, explain it, and request a decision.

## Inspect the target project

Determine:

- the Python and pytest versions and the active dependency manager;
- whether `pytest-run-context` is declared, installed, or already configured;
- where root pytest hooks live and whether plugin auto-loading is disabled;
- whether one pytest process owns the run or an external preparation/cleanup workflow does;
- whether pytest-xdist or multiple processes are involved;
- the narrowest existing validation commands.

Inspect the installed package version and its public exports. Prefer its bundled README and skill
references over assumptions from another version. Do not copy examples whose imports or signatures
do not exist in that version.

## Design the integration

Read [references/lifecycle.md](references/lifecycle.md) before selecting lifecycle ownership. Read
[references/storage-selection.md](references/storage-selection.md) when persistence, `--run-id`,
xdist, or cross-process access is required.

Use the project's existing dependency manager and dependency grouping. Install the Redis extra
only when Redis is selected. Do not add `library-skills` as a runtime dependency.

The pytest plugin is normally registered once through its `pytest11` entry point. Do not also add
`pytest_plugins` or manually register another plugin instance. If plugin auto-loading is disabled,
investigate the project's explicit plugin-loading convention before proposing a change.

The minimal integration may need no `configure()` call: without it, the installed version uses its
default custom model and storage. When project-specific context or persistence is required, keep
configuration in the existing root `conftest.py` and call the installed public `configure()` API
once from `pytest_configure`.

Present any material lifecycle or storage choice and its consequences before editing. Preserve
unrelated hooks and configuration, and make repeated application idempotent.

## Verify

Run the narrowest collection or test command first, then the project's relevant quality checks.
Confirm that:

- pytest loads exactly one plugin instance;
- the session fixture and accessor expose one context within the supported execution model;
- the selected lifecycle creates or loads the expected run;
- persistent storage is reachable without exposing credentials;
- no existing test or reporting configuration was displaced.

Report changed files, lifecycle ownership, storage limitations, and the commands actually run.
