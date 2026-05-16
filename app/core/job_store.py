from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Optional

from app.core.cache import RECIPE_PREVIEW_JOB_CACHE_TTL_SECONDS, recipe_preview_job_cache
from app.core.logging import get_logger
from app.core.redis_client import get_redis_client

logger = get_logger(__name__)


class InMemoryJobStore:
    """Job store backed by the process-local TTL cache. Lost on server restart."""

    def get(self, key: str) -> Optional[dict[str, Any]]:
        job = recipe_preview_job_cache.get(key)
        return deepcopy(job) if job is not None else None

    def set(self, key: str, value: dict[str, Any], ttl_seconds: Optional[float] = None) -> None:
        recipe_preview_job_cache.set(key, deepcopy(value), ttl_seconds=ttl_seconds)


class RedisJobStore:
    """Job store backed by Redis. Survives server restarts."""

    _KEY_PREFIX = "forkfolio:recipe_preview_job:"

    def __init__(self, client: Any) -> None:
        self._client = client
        self._default_ttl = int(RECIPE_PREVIEW_JOB_CACHE_TTL_SECONDS)

    def get(self, key: str) -> Optional[dict[str, Any]]:
        try:
            raw = self._client.get(f"{self._KEY_PREFIX}{key}")
            return json.loads(raw) if raw is not None else None
        except Exception as exc:
            logger.warning("RedisJobStore.get failed. job_id=%s error=%s", key, exc)
            return None

    def set(self, key: str, value: dict[str, Any], ttl_seconds: Optional[float] = None) -> None:
        ttl = int(ttl_seconds) if ttl_seconds is not None else self._default_ttl
        try:
            self._client.setex(f"{self._KEY_PREFIX}{key}", ttl, json.dumps(value))
        except Exception as exc:
            logger.warning("RedisJobStore.set failed. job_id=%s error=%s", key, exc)


def _build_job_store() -> InMemoryJobStore | RedisJobStore:
    client = get_redis_client()
    if client is not None:
        logger.info("Recipe preview job store: Redis")
        return RedisJobStore(client)
    logger.info("Recipe preview job store: in-memory (jobs lost on restart)")
    return InMemoryJobStore()


recipe_preview_job_store: InMemoryJobStore | RedisJobStore = _build_job_store()
