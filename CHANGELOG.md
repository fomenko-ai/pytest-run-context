# Changelog

All notable changes to this project will be documented in this file.

This project follows semantic versioning while the public API is still in `0.x`.

## [0.2.0] - 2026-10-25

### Added

- Added `with_run_context(ProjectContext)` for synchronous helper functions. It injects the
  active context as the first argument, checks the expected custom model (including subclasses),
  and preserves static typing for the remaining arguments and return value.
- Added a conditional `typing-extensions` runtime dependency for Python 3.9 decorator typing;
  Python 3.10+ uses standard-library `typing`.
- Added the packaged `refactor-to-with-run-context` skill to migrate helpers to typed context
  injection while preserving field validation and explicit persistence.
- Added decorated helper calls from session fixtures in all six example `conftest.py` files.

### Changed

- Updated the four existing agent skills to use the decorator for synchronous helpers during
  active pytest sessions, retaining fixture-based context access in tests.

## [0.1.0] - 2026-10-11

### Added

- Added immutable `RunInfo`, extensible `BaseCustomContext`, and one shared mutable
  `RunContext` per pytest session.
- Added explicit project configuration through `configure()`, the `run_context`
  fixture, and `get_run_context()` for code outside fixtures.
- Added standalone `RunContext.create()`, `RunContext.load()`, and
  `RunContext.finish()` APIs for workflows that prepare and finalize context
  outside pytest, with explicit lifecycle ownership and clear errors for
  missing, invalid, or already finished runs.
- Added session lifecycle callbacks with initial and final persistence, plus
  explicit intermediate snapshots through `RunContext.save()`.
- Added in-memory, JSON file, SQLite, and Redis storage backends behind the
  common `Storage` protocol. Redis supports configurable TTL renewed on every
  write and configurable connection retries through `RedisStorage.from_url()`.
- Added atomic duplicate `run_id` rejection for every storage backend.
- Added persistent JSON and SQLite storage without implicit expiry.
- Added guaranteed storage cleanup after successful session initialization,
  including when final persistence fails.
- Added pytest-xdist support with one controller-owned logical run, shared
  worker loading, and controller reload before finalization. Externally owned
  runs remain explicit-save only, and incompatible in-memory multi-process
  use fails clearly.
- Added Python 3.9 through 3.14 compatibility coverage, inline type information,
  and the PEP 561 `py.typed` marker.
- Added runnable examples for every bundled storage backend, standalone pytest
  ownership, and externally prepared multi-process lifecycles.
- Added four packaged Agent Skills for setup, configuration, reporting
  integration, and migration workflows, without additional runtime
  dependencies.
