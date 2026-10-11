# 0001: RunContext finish failure semantics and recovery strategy

Status: superseded by [0002](0002-xdist-lifecycle-and-explicit-save.md)
Date: 2026-10-10
Task: Support creating and loading RunContext outside pytest

## Context

This record describes the original single-process lifecycle. Its completion failure analysis
remains applicable, but its pytest session ownership and automatic-save decision is replaced by
[0002](0002-xdist-lifecycle-and-explicit-save.md).

Finishing a run combines three operations that cannot share one transaction: executing the user's
`on_run_finish()` hook, updating immutable `RunInfo` with `finished_at`, and persisting both
`RunInfo` and the mutable custom context through an arbitrary `Storage` implementation. The hook
may mutate the custom context or perform external actions. Storage may fail before or after the
caller can determine whether a write succeeded.

The existing storage protocol provides create, load, save, and finish operations, but it does not
provide compare-and-swap, distributed locking, or transactions spanning user code and storage.

## Decision

`RunContext.finish()` performs these steps in order:

1. Reject a context whose `finished_at` is already set.
2. Prepare a new immutable `RunInfo` containing the completion time.
3. Call `custom.on_run_finish(final_info)`.
4. Apply `final_info` to the in-memory context without replacing the custom model.
5. Persist the final info and custom state through `Storage.finish_run()`.

There is no automatic rollback, retry, or recovery mechanism. Hook exceptions and storage
exceptions are propagated to the caller.

When pytest creates a context because `--run-id` is absent, pytest owns that lifecycle and calls
`finish()` at session completion. When pytest loads an externally created context through
`--run-id`, it saves session changes but does not finish the context. The external owner finishes
the run after all workflow stages are complete.

## Guarantees and limitations

During an ordinary successful completion, the finish hook is invoked once, its changes are stored
with `finished_at`, and another call to `finish()` on that context is rejected.

This is not an exactly-once or at-most-once guarantee across failures. The hook and storage write
are not jointly atomic. A retry after an uncertain result may repeat the hook and any external side
effects. Checking in-memory `finished_at` does not prevent two processes from concurrently
finishing copies of the same run.

## Failure scenarios

- If the hook mutates some fields and then raises, final info is not applied and storage is not
  called. Partial in-memory custom mutations remain.
- If the hook performs an external action and then raises, that action is not rolled back.
- If the hook succeeds but storage rejects the write, final info and hook mutations may remain in
  memory while storage retains an older state.
- If storage commits but acknowledgement is lost, the caller cannot know whether persistence
  succeeded and a manual retry may repeat the hook.
- If the process exits between the hook and persistence, hook effects may exist without a final
  stored state.
- If two processes finish one run concurrently, both may invoke hooks and the last storage write
  may win because the protocol has no compare-and-swap operation.
- Reloading after a failed attempt reflects only the state that storage successfully retained. A
  later finish attempt may invoke the hook again.

## Alternatives considered

The following options remain possible future improvements but are not part of this decision:

- Copying the custom model before invoking the hook.
- Rolling back in-memory mutations.
- Adding a persisted `finishing` state.
- Requiring lifecycle hooks to be idempotent.
- Optimistic locking or compare-and-swap in the storage contract.
- Transactional completion for storage implementations that support it.
- A recovery API.
- An outbox for external side effects.

Each option adds behavioral or storage complexity and none can provide a general transaction over
arbitrary user hooks and all supported backends.

## Consequences

### Positive

- Hook changes and `finished_at` are written together in successful runs.
- The implementation remains independent of pytest and works with the existing storage protocol.
- Ownership is explicit for external multi-stage workflows.

### Negative

- In-memory and stored state can diverge after failure.
- External hook effects can be repeated.
- Concurrent completion is not protected.

## Documentation

- The public lifecycle and external preparation workflow will be documented in `README.md` and
  the runnable examples as part of this feature.
