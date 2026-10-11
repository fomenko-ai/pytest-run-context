---
name: migrate-to-pytest-run-context
description: Migrate an existing custom pytest run-context implementation to pytest-run-context. Use when the project already has context fixtures, hooks, models, globals, or metadata persistence that must be mapped to the library without silently changing behavior. Do not use for a fresh installation with no legacy implementation.
---

# Migrate to pytest-run-context

Replace only the parts of a custom run-context implementation covered by the installed library,
while making unsupported behavior and breaking changes explicit.

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

## Inventory the existing behavior

Search for all context fixtures, accessors, pytest hooks, Pydantic or dataclass models, mutable
globals, service locators, CLI options, preparation/cleanup scripts, storage adapters, serialization,
reporting bridges, and tests. Trace imports and call sites before deciding that code is unused.

Record observable behavior, including:

- creation, loading, saving, and completion timing;
- lifecycle ownership across pytest and external processes;
- context identity and thread/process expectations;
- defaults, validation, and schema evolution;
- duplicate-ID and missing-run behavior;
- concurrency, merging, expiry, retry, and cleanup semantics;
- reporting or test-outcome responsibilities mixed into the legacy context.

Inspect the installed `pytest-run-context` version and only its public API.

## Build a compatibility map

Read [references/compatibility-matrix.md](references/compatibility-matrix.md), then produce a
project-specific table with columns for legacy behavior, current call sites, library equivalent,
compatibility, required change, and risk. Mark behavior as direct, adaptable, unsupported, or
intentionally retained outside the plugin.

Do not force reporting, outcome collection, automatic per-test saves, merge semantics, background
work, or secret storage into `pytest-run-context`; keep such behavior in its existing owning layer
unless the user separately approves redesign.

## Plan and obtain approval

Read [references/migration-checklist.md](references/migration-checklist.md). Propose the smallest
staged migration that preserves behavior, with exact files, compatibility adapters if needed,
validation, rollback points, and known breaking changes.

Obtain explicit user approval before changing existing behavior. Also request a decision when
lifecycle ownership, Storage, concurrency semantics, schema defaults, or deprecation timing has
multiple materially different answers. Do not edit while those questions remain open.

## Implement and verify

After approval, introduce the library integration before removing legacy paths. Preserve unrelated
hooks and reporting. Verify old and new observable behavior with focused tests, then the project's
quality checks. Exercise external lifecycle and persistence boundaries when present.

Delete obsolete code only after its call sites are migrated and replacement behavior is confirmed.
Do not remove compatibility shims, stored data, configuration keys, or CLI options merely because
the new happy path works; follow the approved deprecation plan.

Report migrated and retained responsibilities, behavioral differences, data compatibility,
verification results, and any cleanup intentionally deferred.
