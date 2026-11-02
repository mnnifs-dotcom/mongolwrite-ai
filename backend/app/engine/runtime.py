from __future__ import annotations

import threading
import time

from app.core.config import settings
from app.engine.hunspell_candidates import harvest_safe
from app.engine.metrics import record
from app.engine.models import Correction
from app.engine.pipeline import LanguageEngine

_engine: LanguageEngine | None = None
_lock = threading.Lock()
# Allow concurrent checks so multi-user load does not queue behind one lock.
# Cap via CHECK_CONCURRENCY — Hunspell/spylls is CPU-heavy.
_check_slots = threading.Semaphore(max(1, int(settings.check_concurrency or 3)))
_harvest_lock = threading.Lock()


class CheckBusyError(RuntimeError):
    """Raised when all check slots are busy longer than the wait budget."""


def get_engine() -> LanguageEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = LanguageEngine()
    return _engine


def _harvest_async(text: str) -> None:
    """Fire-and-forget so check latency stays low.

    Skip tiny docs (nothing useful to learn). Very long documents only sample
    the start — full harvest of 1M chars would compete with the live check.
    """
    if len(text.strip()) < 3_000:
        return
    sample = text if len(text) <= 500_000 else text[:500_000]
    engine = get_engine()

    def _run() -> None:
        with _harvest_lock:
            harvest_safe(engine, sample)

    threading.Thread(target=_run, name="hunspell-harvest", daemon=True).start()


def _queue_wait_seconds() -> float:
    raw = getattr(settings, "check_queue_wait_seconds", 8.0)
    try:
        return max(0.5, float(raw))
    except (TypeError, ValueError):
        return 8.0


def run_engine_check(text: str, style: str) -> list[Correction]:
    engine = get_engine()
    t0 = time.perf_counter()
    wait = _queue_wait_seconds()
    acquired = _check_slots.acquire(timeout=wait)
    if not acquired:
        raise CheckBusyError(
            f"check slots full after {wait:.0f}s "
            f"(concurrency={max(1, int(settings.check_concurrency or 3))})"
        )
    try:
        result = engine.check(text, style=style)
    finally:
        _check_slots.release()
    record((time.perf_counter() - t0) * 1000)
    _harvest_async(text)
    return result
