"""Shared Redis client for the backend.

Returns a connected `redis.Redis` instance when `REDIS_URL` is set, otherwise
`None`. Callers should treat `None` as "Redis not configured" and fall back to
in-process behavior. Render wires `REDIS_URL` automatically via `render.yaml`.
"""

from __future__ import annotations

import os
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

_client: Optional["object"] = None
_initialized = False


def _redact(url: str) -> str:
    if "@" not in url:
        return url
    scheme, _, tail = url.partition("://")
    _, _, host_part = tail.partition("@")
    return f"{scheme}://****@{host_part}"


def get_redis_client():
    """Return a process-wide Redis client, or `None` if `REDIS_URL` is unset."""
    global _client, _initialized
    if _initialized:
        return _client

    _initialized = True
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        logger.info("REDIS_URL not set; Redis client disabled")
        return None

    try:
        import redis

        _client = redis.Redis.from_url(redis_url, decode_responses=True)
        logger.info("Redis client initialized (%s)", _redact(redis_url))
    except Exception as exc:
        logger.warning("Redis client init failed; running without Redis: %s", exc)
        _client = None
    return _client
