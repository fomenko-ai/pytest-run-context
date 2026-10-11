# Migration checklist

## Discovery

- Locate definitions and every import or indirect registration of the current context.
- Identify plugin auto-loading, `pytest_plugins`, hook modules, root and nested `conftest.py` files.
- Trace preparation, pytest, cleanup, and reporting processes separately.
- Identify stored formats, existing run IDs, retention, migrations, and operational tooling.
- Record thread, xdist, multiprocessing, and concurrent-writer assumptions.
- Find tests that define the current contract, including failure and resource cleanup paths.

## Design

- Choose pytest-owned or externally owned lifecycle explicitly.
- Map project data to a `BaseCustomContext` subclass; keep plugin-owned `RunInfo` minimal.
- Choose Storage from actual durability and sharing requirements.
- Decide whether old stored runs must remain readable; the library has no generic schema migration
  facility.
- Keep reporting and outcome collection outside the plugin.
- Define a compatibility period when callers cannot move atomically.
- List each breaking change and obtain approval before implementation.

## Implementation

- Add the dependency using the existing dependency manager.
- Configure the auto-loaded plugin once; do not register a duplicate plugin.
- Replace accessors and fixtures incrementally where a safe seam exists.
- Use explicit `save()` at required persistence boundaries.
- Ensure the correct owner calls `finish()` once in the successful workflow.
- Preserve guaranteed Storage cleanup with `try/finally` for standalone use.
- Keep secrets out of models, serialized state, examples, and logs.

## Validation and cleanup

- Test context identity, validation, lifecycle callback counts, and timestamps.
- Test initial, explicit, and final persistence plus duplicate and missing IDs.
- Test error propagation and Storage cleanup.
- Test xdist or cross-process behavior only with a shared backend.
- Inspect reports if the old implementation supplied reporting metadata.
- Run existing tests before deleting legacy code.
- Search again for old imports, configuration, CLI flags, stored-format readers, and dead adapters.
- Remove obsolete code only after the replacement is confirmed and approved.
