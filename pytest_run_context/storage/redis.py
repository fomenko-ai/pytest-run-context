from importlib import import_module
from typing import Optional

from .base import RunAlreadyExistsError, StoredRun


class RedisStorage:
    def __init__(
        self, client, ttl_seconds: int = 86400, prefix: str = "pytest-run"
    ) -> None:
        if ttl_seconds < 0:
            raise ValueError("ttl_seconds must be >= 0")
        self._client = client
        self._ttl = ttl_seconds
        self._prefix = prefix
        self._owns_client = False

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        port: int = 6379,
        database: int = 0,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ttl_seconds: int = 86400,
        prefix: str = "pytest-run",
        retry_count: int = 3,
        retry_backoff_base: float = 0.008,
        retry_backoff_cap: float = 0.512,
    ) -> "RedisStorage":
        if retry_count < 0:
            raise ValueError("retry_count must be >= 0")

        redis = import_module("redis")
        backoff = import_module("redis.backoff")
        retry_module = import_module("redis.retry")

        retry = retry_module.Retry(
            backoff.ExponentialBackoff(
                base=retry_backoff_base,
                cap=retry_backoff_cap,
            ),
            retries=retry_count,
        )
        client = redis.Redis.from_url(
            url,
            port=port,
            db=database,
            username=username,
            password=password,
            retry=retry,
        )
        storage = cls(client, ttl_seconds=ttl_seconds, prefix=prefix)
        storage._owns_client = True
        return storage

    def _key(self, run_id: str) -> str:
        return f"{self._prefix}:{run_id}"

    def _write(self, run_id: str, info: str, custom: str, *, create: bool) -> None:
        # Lua script makes uniqueness checks, writes and TTL changes atomic.
        script = """
        local exists = redis.call('EXISTS', KEYS[1])
        if ARGV[4] == '1' and exists == 1 then return 0 end
        if ARGV[4] == '0' and exists == 0 then return -1 end
        redis.call('HSET', KEYS[1], 'info', ARGV[1], 'custom', ARGV[2])
        local ttl = tonumber(ARGV[3])
        if ttl > 0 then redis.call('EXPIRE', KEYS[1], ttl)
        else redis.call('PERSIST', KEYS[1]) end
        return 1
        """
        result = self._client.eval(
            script,
            1,
            self._key(run_id),
            info,
            custom,
            self._ttl,
            "1" if create else "0",
        )
        if result == 0:
            raise RunAlreadyExistsError(run_id)
        if result == -1:
            raise KeyError(run_id)

    def create_run(self, run_id: str, info: str, custom: str) -> None:
        self._write(run_id, info, custom, create=True)

    def save_run(self, run_id: str, info: str, custom: str) -> None:
        self._write(run_id, info, custom, create=False)

    def load_run(self, run_id: str) -> Optional[StoredRun]:
        data = self._client.hgetall(self._key(run_id))
        if not data:
            return None

        def decode(value):
            return value.decode() if isinstance(value, bytes) else value

        return StoredRun(
            decode(data.get(b"info", data.get("info"))),
            decode(data.get(b"custom", data.get("custom"))),
        )

    def finish_run(self, run_id: str, info: str, custom: str) -> None:
        self.save_run(run_id, info, custom)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()
