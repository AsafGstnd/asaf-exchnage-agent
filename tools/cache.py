"""
Simple in-memory cache with TTL for RAG, web search, and agent responses.
Reduces LLM and external API calls to stay within budget.
"""
import hashlib
import json
import time
import threading
from typing import Any, Callable, Optional

# Default TTL in seconds (1 hour)
CACHE_TTL = 3600
CACHE_MAX_SIZE = 1000


class TTLCache:
    """Thread-safe in-memory cache with TTL."""

    def __init__(self, ttl: int = CACHE_TTL, max_size: int = CACHE_MAX_SIZE):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._ttl = ttl
        self._max_size = max_size
        self._lock = threading.Lock()

    def _make_key(self, *parts: str) -> str:
        combined = "|".join(parts)
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            value, expires_at = self._cache[key]
            if time.time() > expires_at:
                del self._cache[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._cache) >= self._max_size:
                # Evict oldest entries
                to_remove = sorted(
                    self._cache.items(), key=lambda x: x[1][1]
                )[: self._max_size // 4]
                for k, _ in to_remove:
                    del self._cache[k]
            self._cache[key] = (value, time.time() + self._ttl)


_rag_cache = TTLCache(ttl=CACHE_TTL, max_size=CACHE_MAX_SIZE)
_web_cache = TTLCache(ttl=CACHE_TTL, max_size=CACHE_MAX_SIZE)
_agent_cache = TTLCache(ttl=CACHE_TTL, max_size=100)


def _cache_key(*parts: str) -> str:
    combined = "|".join(str(p) for p in parts)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def cached_rag_search(query: str, university: Optional[str] = None, top_k: int = 3, filter_dict: Optional[dict] = None, fetch_fn: Optional[Callable] = None) -> Any:
    """Execute RAG search with cache. Cache key: hash(query + university + filter)."""
    key_parts = [query, str(university or ""), json.dumps(filter_dict or {}, sort_keys=True)]
    cache_key = _cache_key(*key_parts)
    cached = _rag_cache.get(cache_key)
    if cached is not None:
        return cached
    if fetch_fn is None:
        from tools.implementations import rag_search_tool
        result = rag_search_tool(query=query, university=university, top_k=top_k, filter=filter_dict)
    else:
        result = fetch_fn(query=query, top_k=top_k, filter=filter_dict)
    _rag_cache.set(cache_key, result)
    return result


def cached_web_search(query: str, top_k: int = 3, fetch_fn: Optional[Callable] = None) -> str:
    """Execute web search with cache. Cache key: hash(query)."""
    cache_key = _cache_key(query)
    cached = _web_cache.get(cache_key)
    if cached is not None:
        return cached
    if fetch_fn is None:
        from tools.implementations import web_search_tool
        result = web_search_tool(query=query, top_k=top_k)
    else:
        result = fetch_fn(query=query, top_k=top_k)
    _web_cache.set(cache_key, result)
    return result


def get_agent_cache_key(user_profile: dict) -> str:
    """Cache key for agent responses: hash(user_profile)."""
    return _cache_key(json.dumps(user_profile, sort_keys=True))


def get_cached_agent_response(key: str) -> Optional[Any]:
    return _agent_cache.get(key)


def set_cached_agent_response(key: str, value: Any) -> None:
    _agent_cache.set(key, value)
