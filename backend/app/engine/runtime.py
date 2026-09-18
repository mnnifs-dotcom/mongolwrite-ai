from __future__ import annotations

import threading

from app.engine.hunspell_candidates import harvest_safe
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
    """Fire-and-forget so check latency stays low."""
    if not text.strip():
        return
    engine = get_engine()

    def _run() -> None:
        with _harvest_lock:
            harvest_safe(engine, text)

    threading.Thread(target=_run, name="hunspell-harvest", daemon=True).start()


def run_engine_check(text: str, style: str) -> list[Correction]:
    engine = get_engine()
    with _check_lock:
        result = engine.check(text, style=style)
    _harvest_async(text)
    return result
