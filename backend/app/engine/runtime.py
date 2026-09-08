from __future__ import annotations

import threading

from app.engine.models import Correction
from app.engine.pipeline import LanguageEngine

_engine: LanguageEngine | None = None
_lock = threading.Lock()
_check_lock = threading.Lock()


def get_engine() -> LanguageEngine:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = LanguageEngine()
    return _engine


def run_engine_check(text: str, style: str) -> list[Correction]:
    engine = get_engine()
    with _check_lock:
        return engine.check(text, style=style)
