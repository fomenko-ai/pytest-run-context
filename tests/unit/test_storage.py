from __future__ import annotations

import sys
from types import ModuleType
from typing import Any, ClassVar

import pytest

from pytest_run_context.storage import (
    MemoryStorage,
    RedisStorage,
    RunAlreadyExistsError,
    StoredRun,
)


class FakeRedisClient:
    def __init__(self, *, bytes_response: bool = True) -> None:
        self.data: dict[str, dict[str, str]] = {}
        self.expiry: dict[str, int | None] = {}
        self.bytes_response = bytes_response
        self.eval_calls: list[tuple[Any, ...]] = []
        self.closed = False

    def eval(
        self,
        script: str,
        key_count: int,
        *args: Any,  # noqa: ANN401 - fake mirrors redis-py's dynamically typed API
    ) -> int:
        self.eval_calls.append((script, key_count, *args))
        key, info, custom, ttl, create_flag = args
        exists = key in self.data
        if create_flag == "1" and exists:
            return 0
        if create_flag == "0" and not exists:
            return -1
        self.data[key] = {"info": info, "custom": custom}
        self.expiry[key] = int(ttl) if int(ttl) > 0 else None
        return 1

    def hgetall(self, key: str) -> dict[Any, Any]:
        values = self.data.get(key)
        if values is None:
            return {}
        if not self.bytes_response:
            return values
        return {field.encode(): value.encode() for field, value in values.items()}

    def close(self) -> None:
        self.closed = True


class FakeExponentialBackoff:
    def __init__(self, *, cap: float, base: float) -> None:
        self.cap = cap
        self.base = base


class FakeRetry:
    def __init__(self, backoff: FakeExponentialBackoff, retries: int) -> None:
        self.backoff = backoff
        self.retries = retries


class FakeRedisFactory:
    client: ClassVar[FakeRedisClient] = FakeRedisClient()
    url: ClassVar[str] = ""
    kwargs: ClassVar[dict[str, Any]] = {}

    @classmethod
    def from_url(
        cls,
        url: str,
        **kwargs: Any,  # noqa: ANN401 - fake mirrors redis-py's dynamically typed API
    ) -> FakeRedisClient:
        cls.url = url
        cls.kwargs = kwargs
        return cls.client


def install_fake_redis_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    redis_module = ModuleType("redis")
    backoff_module = ModuleType("redis.backoff")
    retry_module = ModuleType("redis.retry")
    redis_module.__dict__["Redis"] = FakeRedisFactory
    backoff_module.__dict__["ExponentialBackoff"] = FakeExponentialBackoff
    retry_module.__dict__["Retry"] = FakeRetry
    monkeypatch.setitem(sys.modules, "redis", redis_module)
    monkeypatch.setitem(sys.modules, "redis.backoff", backoff_module)
    monkeypatch.setitem(sys.modules, "redis.retry", retry_module)


def test_memory_storage_contract() -> None:
    storage = MemoryStorage()

    assert storage.load_run("missing") is None
    storage.create_run("r1", "{}", '{"a":1}')
    assert storage.load_run("r1") == StoredRun("{}", '{"a":1}')

    with pytest.raises(RunAlreadyExistsError, match="r1"):
        storage.create_run("r1", "{}", "{}")

    storage.save_run("r1", '{"a":2}', '{"b":3}')
    assert storage.load_run("r1") == StoredRun('{"a":2}', '{"b":3}')

    storage.finish_run("r1", '{"done":true}', "{}")
    assert storage.load_run("r1") == StoredRun('{"done":true}', "{}")


def test_memory_storage_rejects_update_for_missing_run() -> None:
    storage = MemoryStorage()

    with pytest.raises(KeyError, match="missing"):
        storage.save_run("missing", "{}", "{}")

    with pytest.raises(KeyError, match="missing"):
        storage.finish_run("missing", "{}", "{}")


@pytest.mark.parametrize("ttl", [-1, -100])
def test_redis_storage_rejects_negative_ttl(ttl: int) -> None:
    with pytest.raises(ValueError, match="ttl_seconds must be >= 0"):
        RedisStorage(FakeRedisClient(), ttl_seconds=ttl)


@pytest.mark.parametrize("bytes_response", [True, False])
def test_redis_storage_contract_and_response_decoding(bytes_response: bool) -> None:
    client = FakeRedisClient(bytes_response=bytes_response)
    storage = RedisStorage(client, ttl_seconds=60, prefix="tests")

    assert storage.load_run("missing") is None
    storage.create_run("r1", "info", "custom")
    assert storage.load_run("r1") == StoredRun("info", "custom")
    assert client.expiry["tests:r1"] == 60

    with pytest.raises(RunAlreadyExistsError, match="r1"):
        storage.create_run("r1", "new-info", "new-custom")

    storage.save_run("r1", "saved-info", "saved-custom")
    assert storage.load_run("r1") == StoredRun("saved-info", "saved-custom")
    storage.finish_run("r1", "final-info", "final-custom")
    assert storage.load_run("r1") == StoredRun("final-info", "final-custom")
    storage.close()


def test_redis_storage_rejects_update_for_missing_run() -> None:
    storage = RedisStorage(FakeRedisClient())

    with pytest.raises(KeyError, match="missing"):
        storage.save_run("missing", "info", "custom")


def test_redis_zero_ttl_disables_expiry() -> None:
    client = FakeRedisClient()
    storage = RedisStorage(client, ttl_seconds=0)

    storage.create_run("r1", "info", "custom")

    assert client.expiry["pytest-run:r1"] is None


def test_redis_storage_from_url_configures_retry_and_owns_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_redis_modules(monkeypatch)
    example_password = "example-password"  # noqa: S105 - non-secret test fixture value
    client = FakeRedisClient()
    FakeRedisFactory.client = client

    storage = RedisStorage.from_url(
        "redis://cache.example",
        port=6380,
        database=4,
        username="example-user",
        password=example_password,
        ttl_seconds=120,
        prefix="example",
        retry_count=5,
        retry_backoff_base=0.1,
        retry_backoff_cap=1.5,
    )

    assert FakeRedisFactory.url == "redis://cache.example"
    assert FakeRedisFactory.kwargs["port"] == 6380
    assert FakeRedisFactory.kwargs["db"] == 4
    assert FakeRedisFactory.kwargs["username"] == "example-user"
    assert FakeRedisFactory.kwargs["password"] == example_password
    retry = FakeRedisFactory.kwargs["retry"]
    assert isinstance(retry, FakeRetry)
    assert retry.retries == 5
    assert retry.backoff.base == 0.1
    assert retry.backoff.cap == 1.5

    storage.create_run("r1", "info", "custom")
    assert client.expiry["example:r1"] == 120
    storage.close()
    assert client.closed is True


def test_redis_storage_does_not_close_injected_client() -> None:
    client = FakeRedisClient()

    RedisStorage(client).close()

    assert client.closed is False


def test_redis_storage_from_url_rejects_negative_retry_count() -> None:
    with pytest.raises(ValueError, match="retry_count must be >= 0"):
        RedisStorage.from_url("redis://localhost", retry_count=-1)
