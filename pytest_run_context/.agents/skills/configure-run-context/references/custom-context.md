# Custom context models

`BaseCustomContext` is the intended project extension point. It is a Pydantic model configured with
assignment validation and forbidden extra fields.

Define only non-secret metadata with a current project requirement. Prefer explicit types and
`Field(default_factory=...)` for mutable defaults. Required fields without defaults prevent the
plugin from creating a new context because version 0.1.0 constructs the model with no arguments.

```python
from pydantic import Field
from pytest_run_context import BaseCustomContext, RunInfo


class ProjectContext(BaseCustomContext):
    environment: str = "dev"
    service_versions: dict[str, str] = Field(default_factory=dict)

    def on_run_start(self, info: RunInfo) -> None:
        self.service_versions.clear()

    def on_run_finish(self, info: RunInfo) -> None:
        pass
```

Use lifecycle callbacks only for project-owned metadata behavior:

- `on_run_start(info)` runs once during `RunContext.create()` and before initial persistence.
- `on_run_finish(info)` runs during `finish()` with `finished_at` populated and before final
  persistence.
- Loading never invokes the start callback.
- `save()` invokes neither callback.

Callbacks may fail and are not transactional with arbitrary external effects. Avoid hidden network
work, result collection, reporting, retries, and secret logging unless separately required and
designed by the consuming project.

`RunInfo` contains only `run_id`, `started_at`, and `finished_at`. It is frozen. Do not add or
simulate status, statistics, test outcomes, or report data in plugin-owned metadata.
