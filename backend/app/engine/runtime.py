from __future__ import annotations

import threading
import time

from app.engine.hunspell_candidates import harvest_safe
from app.engine.metrics import record
from app.engine.models import Correction
from app.engine.pipeline import LanguageEngine

_engine: LanguageEngine | None = None
_lock = threading.Lock()
_check_lock = threading.Lock()
_harvest_lock = threading.Lock()


def get_engine() -> LanguageEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = LanguageEngine()
    return _engine


def _harvest_async(text: str) -> None:
    """Fire-and-forget so check latency stays low.

    Very long documents only sample the start — full harvest of 1M chars
    would compete with the live check for CPU/RAM.
    """
    if not text.strip():
        return
    sample = text if len(text) <= 80_000 else text[:80_000]
    engine = get_engine()

    def _run() -> None:
        with _harvest_lock:
            harvest_safe(engine, sample)

    threading.Thread(target=_run, name="hunspell-harvest", daemon=True).start()


def run_engine_check(text: str, style: str) -> list[Correction]:
    engine = get_engine()
    t0 = time.perf_counter()
    with _check_lock:
        result = engine.check(text, style=style)
    record((time.perf_counter() - t0) * 1000)
    _harvest_async(text)
    return result
