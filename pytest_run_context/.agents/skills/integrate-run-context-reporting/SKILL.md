---
name: integrate-run-context-reporting
description: Pass pytest-run-context metadata into an existing test reporting system. Use when the user asks to expose run IDs or approved custom context fields in JUnit XML, Allure, ReportPortal, or another established reporting pipeline. Do not use to build a reporting framework or collect test outcomes in pytest-run-context.
---

# Integrate run context with reporting

Bridge selected run metadata into reporting infrastructure already owned by the target project.
`pytest-run-context` 0.1.0 has no native reporting integration and does not collect test outcomes.

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

## Inspect the reporting pipeline

Identify the exact reporter and installed version, how it is configured, where metadata is already
attached, which report artifact is authoritative, and whether the project already has a bridge for
session metadata. Inspect the installed reporter's documented public extension API. Do not infer a
native integration merely because both plugins run under pytest.

Determine the requested scope:

- run-level identity or metadata;
- per-test properties, labels, parameters, or attributes;
- a link or key used by external dashboards;
- which fields are explicitly approved for disclosure.

If the desired report location, cardinality, or disclosure policy is unclear and materially changes
the implementation, ask before editing.

## Design the bridge

Read [references/reporting-patterns.md](references/reporting-patterns.md) for reporter-specific
boundaries and validation.

Obtain context only through the public `run_context` fixture or `get_run_context()` during the
active session. Select an explicit allowlist of fields. Prefer stable identifiers and small scalar
values; do not serialize the complete custom model into reports.

Use the installed reporting plugin's documented public mechanism. Keep the bridge in the consuming
project and preserve existing reporter configuration, hooks, markers, and command-line options.
Avoid hook-order assumptions unless the installed versions document them.

Never add test outcome collection, report generation, or reporter-specific APIs to
`pytest-run-context`. Do not treat `save()` as a reporting operation; it persists a context snapshot
only.

## Protect sensitive data

Treat report artifacts as externally visible. Exclude passwords, tokens, connection URLs with
credentials, `SecretStr` values, personal data not approved for reporting, and broad environment
dumps. Redaction after full serialization is not sufficient; build the report payload from an
allowlist.

## Verify the artifact

Run a small representative test with the reporter enabled, then inspect the generated report or
captured reporter payload. Assert the approved field names and values are present in their intended
scope and that sensitive or unrelated context fields are absent. Also run the existing reporting
tests or configuration checks.

Report the bridge point, field allowlist, reporter-version assumptions, artifact inspected, and any
limitations. If end-to-end reporter execution is unavailable, say exactly which static checks ran
and leave the integration unclaimed.
