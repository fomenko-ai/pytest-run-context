# Agent Skills

`pytest-run-context` ships four skills for AI coding agents. They provide version-aware workflows
for integrating the library into a consuming project:

- [`setup-pytest-run-context`](../pytest_run_context/.agents/skills/setup-pytest-run-context/SKILL.md)
  adds the plugin to an existing pytest project and selects lifecycle ownership;
- [`configure-run-context`](../pytest_run_context/.agents/skills/configure-run-context/SKILL.md)
  defines custom context models, persistence, and standalone workflows;
- [`integrate-run-context-reporting`](../pytest_run_context/.agents/skills/integrate-run-context-reporting/SKILL.md)
  passes explicitly approved metadata to an existing reporting system without turning the plugin
  into a reporting framework;
- [`migrate-to-pytest-run-context`](../pytest_run_context/.agents/skills/migrate-to-pytest-run-context/SKILL.md)
  maps and replaces a project's legacy run-context implementation.

The skills are packaged with the library so their instructions stay aligned with the installed
version of `pytest-run-context`.

## Installation

After adding `pytest-run-context` to a project, inspect the skills discovered from installed direct
dependencies:

```bash
uvx library-skills scan --json
```

Install interactively into the agent-neutral `.agents/skills/` directory:

```bash
uvx library-skills
```

After installation, check that managed skill links remain valid:

```bash
uvx library-skills --check
```

Review installed skills as you would any instructions supplied to an AI agent. The skills do not
add runtime dependencies, execute during pytest runs, or change the plugin's runtime behavior.
