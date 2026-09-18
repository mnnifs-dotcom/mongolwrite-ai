from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any, Callable

_log = logging.getLogger(__name__)
_lock = threading.Lock()
_started = time.monotonic()
_samples: deque[tuple[float, float, bool]] = deque(maxlen=2_000)
# (recorded_at_monotonic, duration_ms, is_boot_spike)
_COLD_MS = 3_000.0
_SLOW_MS = 1_500.0
_ready = False
_warmup_ms = 0.0
_last_warm_at = 0.0
_heal_scheduled = False
_on_heal: Callable[[], None] | None = None


def set_heal_handler(handler: Callable[[], None]) -> None:
    global _on_heal
    _on_heal = handler


def mark_ready(*, warmup_ms: float) -> None:
    """Mark service ready and drop boot-time slow samples automatically."""
    global _ready, _warmup_ms, _last_warm_at, _heal_scheduled
    with _lock:
        _ready = True
        _warmup_ms = float(warmup_ms)
        _last_warm_at = time.monotonic()
        _heal_scheduled = False
        kept = [row for row in _samples if not row[2]]
        _samples.clear()
        _samples.extend(kept)


def _schedule_heal() -> None:
    global _heal_scheduled
    with _lock:
        if _heal_scheduled or _on_heal is None:
            return
        _heal_scheduled = True
        handler = _on_heal

    def _run() -> None:
        try:
            handler()
        except Exception:
            _log.exception("auto-heal failed")
        finally:
            global _heal_scheduled
            with _lock:
                _heal_scheduled = False

    threading.Thread(target=_run, name="auto-heal", daemon=True).start()


def record(duration_ms: float) -> None:
    """Record a check duration. Boot spikes are ignored for status and auto-cleared."""
    with _lock:
        ready = _ready
        spike = (not ready) or duration_ms >= _COLD_MS
        if not spike:
            _samples.append((time.monotonic(), float(duration_ms), False))
            return
        # Keep a short memory of spikes for logging, but they must not worry the admin.
        _samples.append((time.monotonic(), float(duration_ms), True))
        should_heal = ready
    if should_heal:
        _schedule_heal()


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100) * (len(ordered) - 1)))))
    return ordered[idx]


def snapshot() -> dict[str, Any]:
    now = time.monotonic()
    day_ago = now - 86_400
    with _lock:
        ready = _ready
        warmup_ms = _warmup_ms
        last_warm = _last_warm_at
        recent = [row for row in _samples if row[0] >= day_ago]
    # Status uses only normal (non-spike) timings.
    normal = [ms for _, ms, spike in recent if not spike]
    spikes = sum(1 for _, _, spike in recent if spike)
    slow = sum(1 for ms in normal if ms >= _SLOW_MS)
    if not ready:
        status = "starting"
        advice = "Сервер асаж байна. Систем өөрөө бэлдэнэ — та юу ч дарах хэрэггүй."
    elif slow >= 8:
        status = "busy"
        advice = "Одоо олон хүн зэрэг ашиглаж байна. Түр удаан байж болно. Та юу ч хийх шаардлагагүй."
    else:
        status = "ready"
        advice = "Бүх зүйл хэвийн. Шалгалт хэвийн хурдтай. Та юу ч дарах хэрэггүй."
    return {
        "status": status,
        "ready": ready,
        "advice": advice,
        "checks_24h": len(normal),
        "warm_p95_ms_24h": round(_percentile(normal, 95)),
        "p95_ms_24h": round(_percentile(normal, 95)),
        "slow_24h": slow,
        "outlier_24h": spikes,
        "warmup_ms": round(warmup_ms),
        "uptime_seconds": int(now - _started),
        "seconds_since_warm": int(now - last_warm) if last_warm else None,
        "auto_heals": True,
    }
