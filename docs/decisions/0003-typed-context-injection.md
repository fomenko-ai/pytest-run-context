# 0003: Typed context injection for helper functions

Status: accepted
Date: 2026-10-25
Task: Add with_run_context(ProjectContext)

## Context

Helper functions outside pytest fixtures need convenient access to the active context with
the consuming project's custom model type. The existing accessor returns a context or raises,
but its return annotation does not identify the configured project model. Static analyzers
cannot derive that type from a separate runtime call to configure().

## Decision

Expose `with_run_context(context_model)` as a decorator for synchronous helper functions.
The decorated function declares `RunContext[T]` as its first positional argument. Callers
omit that argument; ParamSpec and Concatenate preserve the remaining argument and return types.

The model parameter describes the expected custom type. Validate it as a BaseCustomContext
subclass when constructing the decorator. At each function call, resolve the context through
get_run_context(), check the custom model with isinstance, and pass the same context instance.
Accept model subclasses. Propagate the accessor's RuntimeError when unavailable and raise
TypeError before executing the helper when the custom model does not match.

Decoration is allowed before context activation. Invocation requires the plugin's active
context, including when the helper is defined in conftest.py. Preserve function metadata;
do not add pytest signature rewriting, annotation introspection, or a second context registry.
Direct decoration of pytest tests, fixtures, hooks, instance methods, and dedicated async
support are outside this initial contract.

Lifecycle ownership and explicit persistence remain as specified in [0002](0002-xdist-lifecycle-and-explicit-save.md).
Use typing-extensions as a direct dependency only on Python 3.9, with the marker
`python_version < '3.10'`. Import ParamSpec and Concatenate from standard-library typing on
Python 3.10+ and from typing_extensions on Python 3.9. This compatibility refinement was
approved on 2026-10-25 and retains the same public API and supported Python versions.

## Alternatives Considered

### Inject the last argument

This can work at runtime, but ParamSpec and Concatenate do not express removing the last
parameter of an arbitrary signature. It would require signature restrictions or weaker typing.

### Infer the model from configure() or function annotations

Runtime configuration cannot supply static type information. Inspecting function annotations
adds forward-reference resolution and import-order concerns. An explicit expected model makes
the runtime check straightforward and visible at the declaration.

### Use only the accessor or explicit argument passing

Both remain supported. The decorator is an optional convenience for repeated helper calls and
adds runtime verification of the expected custom model.

## Consequences

### Positive

- Helpers receive the existing shared context with a checked custom model type.
- Callers retain static checking of their arguments and the result.
- Persistence, pytest initialization, and storage contracts remain unchanged.

### Negative

- The expected model appears in both the decorator and the function annotation.
- The injected parameter must come first; the initial contract excludes framework-decorated
  functions and bound instance methods.
- The package gains a direct typing-extensions dependency on Python 3.9. Other dependencies,
  including the currently locked Pydantic versions, may still install it on newer Python versions.

## Documentation

- [README.md](../../README.md#access-from-helper-functions)
