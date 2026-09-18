from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any

_log = logging.getLogger(__name__)
_lock = threading.Lock()
_started = time.monotonic()
_samples: deque[tuple[float, float, bool]] = deque(maxlen=2_000)
# (recorded_at_monotonic, duration_ms, is_outlier)
_COLD_MS = 3_000.0
_SLOW_MS = 1_500.0
_ready = False
_warmup_ms = 0.0
_last_warm_at = 0.0


def mark_ready(*, warmup_ms: float) -> None:
    global _ready, _warmup_ms, _last_warm_at
    with _lock:
        _ready = True
        _warmup_ms = float(warmup_ms)
        _last_warm_at = time.monotonic()
        # Drop cold-start samples left over from boot — no admin click needed.
        kept = [row for row in _samples if not row[2]]
        _samples.clear()
        _samples.extend(kept)


def record(duration_ms: float) -> None:
    with _lock:
        ready = _ready
        outlier = (not ready) or duration_ms >= _COLD_MS
        _samples.append((time.monotonic(), float(duration_ms), outlier))


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
    warm = [ms for _, ms, outlier in recent if not outlier]
    all_ms = [ms for _, ms, _ in recent]
    outliers = sum(1 for _, _, outlier in recent if outlier)
    slow = sum(1 for ms in warm if ms >= _SLOW_MS)
    status = "ready" if ready else "starting"
    if ready and slow >= 5:
        status = "busy"
    advice = (
        "Систем бэлэн. Шалгалт хэвийн хурдтай ажиллаж байна."
        if status == "ready"
        else (
            "Сервер дөнгөж аслаа. Толь автоматаар ачаалж байна — админ юу ч дарах шаардлагагүй."
            if status == "starting"
            else "Одоо олон хүсэлт зэрэг ирж байна. Түр удаашралтай байж болно."
        )
    )
    return {
        "status": status,
        "ready": ready,
        "advice": advice,
        "checks_24h": len(recent),
        "warm_p95_ms_24h": round(_percentile(warm, 95)),
        "p95_ms_24h": round(_percentile(all_ms, 95)),
        "slow_24h": slow,
        "outlier_24h": outliers,
        "warmup_ms": round(warmup_ms),
        "uptime_seconds": int(now - _started),
        "seconds_since_warm": int(now - last_warm) if last_warm else None,
    }
