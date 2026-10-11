# Reporting patterns

Start by checking the installed reporter and its documentation. The patterns below identify safe
integration boundaries; they are not native `pytest-run-context` features.

## Shared source data

Within an active pytest session, use `run_context.info.run_id` and an explicit allowlist from
`run_context.custom`. Code outside fixtures may call `get_run_context()`, but only while the context
is active. `RunInfo` supplies timestamps and the run ID, not pass/fail status or test statistics.

Avoid copying `model_dump()` wholesale. Reports often leave the test environment and may retain
data longer than the configured Storage.

## JUnit XML

Pytest can place user properties in JUnit XML through its documented `record_property` fixture.
When the installed pytest version supports the required output mode, a small bridge fixture may
attach allowlisted values per test:

```python
import pytest


@pytest.fixture(autouse=True)
def report_run_id(record_property, run_context) -> None:
    record_property("run_id", run_context.info.run_id)
```

Do not add this globally without confirming that every test should carry the property. Some JUnit
consumers or pytest `junit_family` modes handle custom properties differently. Generate the XML and
inspect parsed test-case properties rather than relying only on console output.

## Allure

There is no built-in bridge. Inspect the installed Allure pytest adapter and use its documented
runtime metadata APIs, such as labels, parameters, links, or environment data, only when they match
the requested scope. Decide deliberately whether a value belongs on every test, one fixture scope,
or an external run-level artifact. Confirm the actual generated Allure result JSON and final report.

Do not write arbitrary context fields into `environment.properties` or labels. These outputs are
commonly published and may expose secrets.

## ReportPortal

There is no built-in bridge. Inspect the installed pytest ReportPortal plugin before choosing an
integration point. Prefer its documented attributes, launch metadata, or logging mechanisms over
private service objects or internal hooks. Preserve existing endpoint, launch, and authentication
configuration, and never copy credentials into `RunContext` or report attributes.

Capture or inspect the emitted payload with the project's fake client or test facility when
possible. A local test must not require a live ReportPortal server unless the user explicitly asks
for that integration environment.

## Other reporters

Apply the same boundary: public context read API, explicit field allowlist, reporter-owned public
extension point, no outcome collection in this plugin, and inspection of the real artifact or a
faithful fake payload.
