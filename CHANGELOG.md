# Changelog

All notable changes to this project will be documented in this file.

This project follows semantic versioning while the public API is still in `0.x`.

## [0.1.0] - 2026-10-10

### Added

- Added immutable `RunInfo`, extensible `BaseCustomContext`, and one shared mutable
  `RunContext` per pytest session.
- Added explicit project configuration through `configure()`, the `run_context`
  fixture, and `get_run_context()` for code outside fixtures.
- Added session lifecycle callbacks with initial and final persistence, plus
  explicit intermediate snapshots through `RunContext.save()`.
- Added in-memory, JSON file, SQLite, and Redis storage backends behind the
  common `Storage` protocol. Redis supports configurable TTL renewed on every
  write and configurable connection retries through `RedisStorage.from_url()`.
- Added atomic duplicate `run_id` rejection for every storage backend.
- Added persistent JSON and SQLite storage without implicit expiry.
- Added guaranteed storage cleanup after successful session initialization,
  including when final persistence fails.
- Added Python 3.9 through 3.14 compatibility coverage, inline type information,
  and the PEP 561 `py.typed` marker.
- Added runnable examples for every bundled storage backend.
