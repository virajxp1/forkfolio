import hashlib
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class _CacheEntry(Generic[T]):
    expires_at: float
    value: T


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: float, max_items: int):
        self._ttl_seconds = ttl_seconds
        self._max_items = max_items
        self._enabled = ttl_seconds > 0 and max_items > 0
        self._data: OrderedDict[str, _CacheEntry[T]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[T]:
        if not self._enabled:
            return None
        now = time.monotonic()
        with self._lock:
            entry = self._data.get(key)
            if not entry:
                return None
            if entry.expires_at <= now:
                self._data.pop(key, None)
                return None
            self._data.move_to_end(key)
            return entry.value

    def set(self, key: str, value: T, ttl_seconds: Optional[float] = None) -> None:
        if not self._enabled:
            return
        ttl = self._ttl_seconds if ttl_seconds is None else ttl_seconds
        if ttl <= 0:
            return
        now = time.monotonic()
        entry = _CacheEntry(expires_at=now + ttl, value=value)
        with self._lock:
            self._data[key] = entry
            self._data.move_to_end(key)
            self._prune(now)

    def delete(self, key: str) -> None:
        if not self._enabled:
            return
        with self._lock:
            self._data.pop(key, None)

    def _prune(self, now: float) -> None:
        expired_keys = [k for k, v in self._data.items() if v.expires_at <= now]
        for key in expired_keys:
            self._data.pop(key, None)
        while len(self._data) > self._max_items:
            self._data.popitem(last=False)


def hash_cache_key(*parts: str) -> str:
    normalized = "\x1f".join(part or "" for part in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


LLM_CACHE_TTL_SECONDS = float(os.getenv("LLM_CACHE_TTL_SECONDS", "3600"))
LLM_CACHE_MAX_ITEMS = int(os.getenv("LLM_CACHE_MAX_ITEMS", "1024"))

llm_text_cache: TTLCache[str] = TTLCache(
    ttl_seconds=LLM_CACHE_TTL_SECONDS, max_items=LLM_CACHE_MAX_ITEMS
)
llm_structured_cache: TTLCache[dict] = TTLCache(
    ttl_seconds=LLM_CACHE_TTL_SECONDS, max_items=LLM_CACHE_MAX_ITEMS
)
