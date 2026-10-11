from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest

from pytest_run_context.storage import (
    RedisStorage,
    RunAlreadyExistsError,
    StoredRun,
)

pytestmark = [pytest.mark.integration, pytest.mark.redis_integration]


@pytest.fixture(scope="module")
def redis_client() -> Iterator[Any]:
    pytest.importorskip("redis")
    container_module = pytest.importorskip("testcontainers.community.redis")

    with container_module.RedisContainer("redis:7.4-alpine") as container:
        client = container.get_client()
        client.ping()
        try:
            yield client
        finally:
            client.close()


@pytest.fixture
def redis_prefix() -> str:
    return f"pytest-run-context-tests:{uuid4()}"


def test_redis_storage_contract_against_real_redis(
    redis_client: Any,  # noqa: ANN401 - third-party client type is loaded dynamically
    redis_prefix: str,
) -> None:
    storage = RedisStorage(redis_client, ttl_seconds=60, prefix=redis_prefix)

    assert storage.load_run("missing") is None
    storage.create_run("r1", "info", "custom")
    assert storage.load_run("r1") == StoredRun("info", "custom")

    with pytest.raises(RunAlreadyExistsError, match="r1"):
        storage.create_run("r1", "new-info", "new-custom")

    storage.save_run("r1", "saved-info", "saved-custom")
    assert RedisStorage(redis_client, prefix=redis_prefix).load_run("r1") == StoredRun(
        "saved-info", "saved-custom"
    )

    storage.finish_run("r1", "final-info", "final-custom")
    assert storage.load_run("r1") == StoredRun("final-info", "final-custom")

    with pytest.raises(KeyError, match="missing"):
        storage.save_run("missing", "info", "custom")


def test_redis_storage_renews_and_disables_ttl(
    redis_client: Any,  # noqa: ANN401 - third-party client type is loaded dynamically
    redis_prefix: str,
) -> None:
    expiring = RedisStorage(redis_client, ttl_seconds=60, prefix=redis_prefix)
    expiring.create_run("expiring", "info", "custom")
    expiring_key = f"{redis_prefix}:expiring"
    assert redis_client.ttl(expiring_key) in range(1, 61)

    redis_client.expire(expiring_key, 1)
    expiring.save_run("expiring", "saved-info", "saved-custom")
    assert redis_client.ttl(expiring_key) in range(59, 61)

    persistent = RedisStorage(redis_client, ttl_seconds=0, prefix=redis_prefix)
    persistent.create_run("persistent", "info", "custom")
    persistent_key = f"{redis_prefix}:persistent"
    assert redis_client.ttl(persistent_key) == -1

    redis_client.expire(persistent_key, 60)
    persistent.save_run("persistent", "saved-info", "saved-custom")
    assert redis_client.ttl(persistent_key) == -1
