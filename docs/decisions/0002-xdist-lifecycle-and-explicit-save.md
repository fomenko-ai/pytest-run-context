# 0002: xdist lifecycle and explicit save semantics

Status: accepted
Date: 2026-10-11
Task: Add pytest-xdist support and unify RunContext persistence

## Context

pytest-xdist runs a controller plus multiple worker processes. The original adapter initialized a
context independently in every process and automatically saved loaded contexts at session end.
Without `--run-id` this produced multiple logical runs. With a shared external ID, the controller's
unchanged final snapshot could overwrite explicit worker saves.

The Storage protocol persists complete snapshots and intentionally has no merge, locking,
versioning, or compare-and-swap operation. Lifecycle ownership must therefore be explicit without
claiming that concurrent custom changes can be combined.

## Decision

Persistence has three explicit sources: `RunContext.create()` writes initial state,
`RunContext.save()` writes a user-requested intermediate snapshot, and `RunContext.finish()` writes
final state. Pytest does not automatically call `save()` for a loaded, externally owned run.

For an xdist run, the controller creates or loads the logical context before workers start and
places its `run_id` in each worker's standard `workerinput`. Workers load independent context
instances and never automatically save or finish them.

When the controller owns the lifecycle, it reloads the latest stored snapshot after workers stop
and calls `finish()` once. When the run was supplied through `--run-id`, neither controller nor
workers finish it; its external owner does so later.

xdist requires Storage shared between processes. Multi-process use with `MemoryStorage` is rejected
with a usage error. pytest-xdist remains a development dependency: the adapter declares its node
hook as optional and ordinary pytest does not require xdist to be installed or loaded.

Concurrent explicit saves retain full-snapshot, last-write-wins semantics. No automatic merge is
provided.

Completion retains the failure policy described by [0001](0001-run-context-finish-failure-semantics.md):
hook and storage failures propagate, cleanup still closes owned resources, and the protocol cannot
guarantee exactly-once external hook effects after uncertain failures.

## Alternatives Considered

### Create a context in every worker

This needs no controller-to-worker communication but produces several logical runs and several
lifecycle executions for one pytest invocation.

### Let the controller keep and finish its initial instance

This preserves a single object in the controller but its stale custom snapshot can overwrite the
last explicit worker save during `finish()`.

### Merge worker changes or add concurrency control

Merging, locks, CAS, or versioning would change the Storage and custom-context contracts. Those
features are outside the current requirement; projects must coordinate concurrent custom updates
when last-write-wins is insufficient.

## Consequences

### Positive

- One xdist invocation maps to one logical run and one lifecycle start/finish pair.
- Explicit worker saves survive controller-owned finalization.
- Ordinary and distributed runs share one persistence rule.
- External orchestration retains exclusive completion ownership.

### Negative

- xdist cannot use MemoryStorage.
- Concurrent worker changes can overwrite one another.
- Finishing a pytest-owned xdist run requires an additional storage read.

## Documentation

- [`README.md`](../../README.md)
- [`docs/xdist-investigation.md`](../xdist-investigation.md)
