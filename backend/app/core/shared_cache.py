"""Optional shared cache (Redis L2) with always-on process L1 semantics.

MongolWrite's hot path is Hunspell membership, not an LLM. Across multiple
APP instances a shared Redis cache avoids repeating the same .lookup() work.
When REDIS_URL is empty or Redis is down, callers keep working with local
in-memory caches only — single-machine Fly stays correct with zero extras.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from app.core.config import settings

_log = logging.getLogger(__name__)

_PREFIX = "mw:hs:v1:"
_DEFAULT_TTL = 60 * 60 * 24 * 14  # 14 days

_lock = threading.Lock()
_client: Any | None = None
_tried = False
_connected = False

# Process-local counters (aggregated into metrics.snapshot).
_stats_lock = threading.Lock()
_stats = {
    "l1_hits": 0,
    "redis_hits": 0,
    "misses": 0,  # had to call Hunspell (or no answer)
    "redis_writes": 0,
    "redis_errors": 0,
}


def cache_stats() -> dict[str, int | float | bool | str]:
    with _stats_lock:
        l1 = int(_stats["l1_hits"])
        redis_hits = int(_stats["redis_hits"])
        misses = int(_stats["misses"])
        writes = int(_stats["redis_writes"])
        errors = int(_stats["redis_errors"])
    total = l1 + redis_hits + misses
    hit_pct = round(100.0 * (l1 + redis_hits) / total, 1) if total else 0.0
    return {
        "enabled": bool(settings.redis_url.strip()),
        "connected": _connected,
        "l1_hits": l1,
        "redis_hits": redis_hits,
        "misses": misses,
        "redis_writes": writes,
        "redis_errors": errors,
        "lookups": total,
        "hit_pct": hit_pct,
        "backend": "redis" if _connected else ("configured" if settings.redis_url.strip() else "memory"),
    }


def record_l1_hit() -> None:
    with _stats_lock:
        _stats["l1_hits"] += 1


def record_miss() -> None:
    with _stats_lock:
        _stats["misses"] += 1


def _get_client() -> Any | None:
    global _client, _tried, _connected
    url = settings.redis_url.strip()
    if not url:
        return None
    with _lock:
        if _tried:
            return _client if _connected else None
        _tried = True
        try:
            import redis  # type: ignore[import-untyped]

            client = redis.Redis.from_url(
                url,
                decode_responses=True,
                socket_connect_timeout=0.4,
                socket_timeout=0.4,
                health_check_interval=30,
            )
            client.ping()
            _client = client
            _connected = True
            _log.info("shared cache: Redis connected")
            return _client
        except Exception as exc:
            _connected = False
            _client = None
            _log.warning("shared cache: Redis unavailable (%s) — using memory only", exc)
            return None


def get_hunspell_membership(folded: str) -> bool | None:
    """Return cached Hunspell bool, or None when unknown."""
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(_PREFIX + folded)
    except Exception:
        with _stats_lock:
            _stats["redis_errors"] += 1
        return None
    if raw is None:
        return None
    with _stats_lock:
        _stats["redis_hits"] += 1
    return raw in {"1", "true", "True"}


def set_hunspell_membership(folded: str, ok: bool, *, ttl: int = _DEFAULT_TTL) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.set(_PREFIX + folded, "1" if ok else "0", ex=ttl)
        with _stats_lock:
            _stats["redis_writes"] += 1
    except Exception:
        with _stats_lock:
            _stats["redis_errors"] += 1


def reset_for_tests() -> None:
    """Clear connection + counters (unit tests only)."""
    global _client, _tried, _connected
    with _lock:
        _client = None
        _tried = False
        _connected = False
    with _stats_lock:
        for key in _stats:
            _stats[key] = 0
