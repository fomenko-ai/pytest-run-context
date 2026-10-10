# Project Coding Rules

These rules apply to AI-assisted code changes in this repository.

1. Before making changes that affect more than two modules or files, propose an architectural
   option first and wait for user approval.
2. Change tests only after the user has approved the changes in the main project code.
3. Delete `*/__pycache__` directories only after an explicit user request.

## Project Architecture

Keep the repository a minimal, reusable pytest plugin for sharing and persisting run context.
Do not add project-specific test behavior, organization addresses, real credentials, or
abstractions without a current requirement. The plugin does not collect test outcomes, produce
reports, or decide which user data to gather.

### Terminology and Configuration Boundaries

Use these terms consistently:

- `RunInfo`: plugin-owned, minimal run metadata (`run_id`, `started_at`, `finished_at`);
- `BaseCustomContext`: Pydantic base model extended by the consuming project;
- `RunContext`: one shared in-memory context for the pytest session, combining `info`, `custom`,
  and `storage`;
- `Storage`: structural protocol for persistence backends;
- `configure()`: the project's explicit dependency configuration entry point;
- `run_context`: pytest fixture exposing the shared context;
- `get_run_context()`: accessor for code outside pytest fixtures.

Respect these ownership rules:

1. The plugin owns context creation, accessibility, persistence, and session lifecycle only.
2. The consuming project owns the schema, collection, and timing of custom metadata updates.
3. `RunInfo` is immutable and contains only minimal plugin-owned metadata. Do not add test
   statistics or status tracking without an explicit requirement.
4. `BaseCustomContext` is a Pydantic model with assignment validation and forbidden extra fields;
   project-specific fields belong in a subclass, not in the plugin.
5. `RunContext` is a regular Python class, not a Pydantic model. Persist `info` and `custom`
   separately as JSON through `Storage`.
6. Never store passwords, tokens, or other secrets in committed files, logs, or sample context
   data. Do not commit `.env` files or real credentials.
7. Generate a `run_id` when none is provided. Reject duplicate IDs atomically; never silently
   overwrite an existing run.
8. Do not add automatic per-test saves or test-report hooks. Explicit `context.save()` persists
   intermediate changes; the plugin also persists initial and final state.

### Dependency Direction

Preserve this composition flow:

```text
pytest auto-loads pytest_run_context via pytest11
        -> root conftest.py calls configure(config, context_model=..., storage=...)
        -> pytest plugin manages session lifecycle
        -> RunContext(info, custom, storage)
        -> Storage protocol
        -> concrete storage implementation
```

Follow these constraints:

1. Use constructor dependency injection and composition over inheritance, except for the
   intended extension of `BaseCustomContext` by consuming projects.
2. Automatically register the plugin once via the `pytest11` entry point. Do not register a
   second plugin instance in the consuming project's `conftest.py`.
3. `configure()` configures the already loaded plugin through the current `pytest.Config`;
   reject repeated configuration. Initialize the context after configuration is available.
4. Keep `RunContext` independent of pytest internals; only the pytest adapter owns hooks and
   fixtures.
5. `RunContext` depends on the `Storage` protocol, not Redis, SQLite, filesystem, or other
   backend-specific APIs. Storage implementations must not depend on project Pydantic models.
6. `run_context` and `get_run_context()` must return the same in-memory instance during the
   active session. Access before initialization or after teardown must fail clearly.
7. The shared context is intentional session state. Do not introduce additional singletons,
   service locators, mutable globals, generic `utils.py`, or unnecessary manager/service layers.
8. Do not promise automatic context propagation to new threads or processes. Explicitly document
   the supported execution model; do not add xdist or multiprocessing support without a requirement.

### Python and Tooling

1. Support the Python versions declared in `pyproject.toml` (currently `>=3.11`) and retain the
   existing `pytest_run_context/` package layout. Do not migrate to `src/` or require Python 3.14
   without an explicit decision.
2. Fully type production and test code.
3. Use Ruff as the only formatter, linter, and import sorter.
4. Use ty for static type checking; do not add mypy.
5. Use `pathlib.Path` for filesystem paths.
6. Keep required runtime dependencies in `[project].dependencies`, optional backend dependencies
   in `[project.optional-dependencies]`, and development-only tools in the `dev` dependency group.
7. Use uv for dependency management and commands. Preserve the automatic `pytest11` entry point.

### Tests and Resource Lifecycle

1. Unit tests must not depend on external networks or services.
2. Integration tests should use fakes, temporary files, and isolated pytest runs; do not require
   a running Redis server for the default test suite.
3. Test context identity across fixture and accessor, explicit saves, initial/final persistence,
   lifecycle callbacks, duplicate IDs, and failure handling.
4. Test storage implementations against the same behavioral contract, including backend-specific
   persistence and expiry rules.
5. Use `try/finally` or equivalent guaranteed cleanup for resources owned by the plugin. Close
   storage even when a lifecycle callback or persistence operation fails.
6. Preserve the agreed error policy: intermediate save failures are reported without automatically
   aborting the pytest run; an unrecoverable final save failure makes the run fail.
7. Keep pytest markers registered and run pytest with `--strict-markers` when markers are used.
8. Do not make ordinary tests depend on a user's project model, configuration, or live infrastructure.

### Context Lifecycle and Storage

1. Create exactly one context per pytest session, after project configuration is supplied.
2. Call `custom.on_run_start(info)` once and persist initial state; call
   `custom.on_run_finish(info)` once and persist final state.
3. The context stays mutable in memory throughout the session; `save()` writes a snapshot and
   is not required for other code in the same process to observe changes.
4. Validate Pydantic state through normal model validation. Do not use unchecked updates to
   bypass validation of immutable `RunInfo`.
5. Keep SQLite and JSON storage persistent indefinitely; do not introduce implicit TTL or
   lazy deletion.
6. Keep Memory storage in memory for the lifetime of its instance, without TTL.
7. Redis TTL defaults to 86,400 seconds, can be disabled with `0`, and is renewed on each write.
   Redis connection retry behavior is configurable; the plugin does not manage Redis containers.
8. Writes that create a run must reject an existing `run_id` atomically in each backend.
9. Do not introduce background saving, heartbeat jobs, per-test collection, reporting artifacts,
   or result aggregation without an explicit requirement.

### Logging and Test Artifacts

1. Use standard Python logging for diagnostics. Do not add a step-logging or reporting framework.
2. Never log passwords, tokens, `SecretStr` values, or complete serialized contexts that may
   contain sensitive user data.
3. Keep generated databases, JSON run files, logs, caches, virtual environments, and other test
   artifacts out of Git.
4. Do not create session artifact directories, JUnit XML, HTML reports, or reporting integrations
   as part of this plugin's responsibility.

### Docker

1. Do not introduce Docker or Docker Compose without a concrete requirement.
2. If container support is added later, keep the build reproducible and exclude `.git`, `.env`,
   credentials, local virtual environments, caches, and generated artifacts from the build context.
3. Never start external storage services implicitly as part of ordinary plugin execution.

## Required Verification

After changing files, run the narrowest relevant check first. Before handing off a completed
change, run the available project quality checks:

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest --strict-markers
```

Additional requirements:

1. Run `uv lock` after dependency metadata changes and verify `uv sync --locked` succeeds when
   a `uv.lock` is maintained. Do not claim lockfile checks succeeded if the lockfile is absent.
2. If a configured pre-commit hook modifies files, accept intended changes and rerun checks until
   they pass without further modifications.
3. Do not report success when a required check was skipped or failed. State the exact reason
   when a check cannot be run.
4. Use temporary directories and fakes for backend integration tests; do not require a live
   Redis server for the standard quality gate.

## Agent Work Records

1. Store resumable task state in `.agent-work/active/`, using one file per issue or independently
   deliverable change.
2. Read the applicable task file before changing code, then verify its claims against the current
   Git status, diff, and source files.
3. Keep the task's current state, plan, verification results, blockers, and next action current.
4. Update the task file after a significant milestone, decision, failed check, or before ending an
   unfinished work session.
5. Never store credentials, secrets, raw logs, or private reasoning in task files.
6. Do not modify a task owned by another active worker without coordination.
7. When a task is complete, move lasting knowledge into regular project documentation, reduce the
   task file to a short result and verification summary, and move it to `.agent-work/completed/`.

## Architecture Decisions

1. Create a decision record in `docs/decisions/` only for a significant, long-lived architectural
   choice with meaningful alternatives or consequences.
2. Use `docs/decisions/template.md` if it exists; otherwise establish a template before the first
   decision record. Do not create records for routine implementation details.
3. Keep accepted decision records in Git. Mark replaced records as `superseded` and link to the
   replacement instead of deleting them.
4. Update regular project documentation after accepting a decision so it continues to describe
   current behavior; a decision record explains why the choice was made.
5. Before changing plugin initialization, `configure()`, the public context API, or the storage
   contract, review applicable existing decision records if any. Do not refer to decision files
   from the hardware-test project.

## Commit Message Rules

Follow the existing linear commit history style:

1. Use an English Conventional Commit subject: `<type>: <imperative summary>`.
2. Prefer the existing types: `feat`, `fix`, `refactor`, and `chore`.
3. Keep the subject short, lowercase after the type, and without a trailing period.
4. Do not add a scope unless it materially clarifies a broad or ambiguous change.
5. Base the message on the staged diff (`git diff --cached`), not on unrelated working-tree changes.
6. For broad commits, name the dominant user-visible change in the subject and put supporting
   refactors, docs, or tests in the body only when needed.
