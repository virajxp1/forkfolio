import pytest

from app.core.job_store import JobStoreUnavailableError, RedisJobStore


class FailingRedisClient:
    def get(self, key: str) -> None:
        del key
        raise ConnectionError("redis unavailable")

    def setex(self, key: str, ttl: int, value: str) -> None:
        del key, ttl, value
        raise ConnectionError("redis unavailable")


def test_redis_job_store_get_raises_when_redis_unavailable() -> None:
    store = RedisJobStore(FailingRedisClient())

    with pytest.raises(JobStoreUnavailableError):
        store.get("job-id")


def test_redis_job_store_set_raises_when_redis_unavailable() -> None:
    store = RedisJobStore(FailingRedisClient())

    with pytest.raises(JobStoreUnavailableError):
        store.set("job-id", {"status": "queued"})
