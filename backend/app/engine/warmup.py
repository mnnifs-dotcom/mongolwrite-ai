from __future__ import annotations

import asyncio
import logging
import time

from app.engine.dictionary import load_hunspell
from app.engine.metrics import mark_ready, record, set_heal_handler
from app.engine.runtime import get_engine

_log = logging.getLogger(__name__)
_KEEP_WARM_SECONDS = 10 * 60


def warm_now() -> dict[str, float | bool]:
    """Load Hunspell and run sample checks so users never hit a slow first request."""
    _install_auto_heal()
    t0 = time.perf_counter()
    hun = load_hunspell()
    engine = get_engine()
    _ = engine.dictionary.has_hunspell
    # Mark ready before sample checks so they count as normal traffic, not boot spikes.
    mark_ready(warmup_ms=0)
    for sample in (
        "бэлэн",
        "ажилтангууд одөр",
        "байгууллага хүсэлт",
        # Prime caches for long official text so the first 50k+ check is not ice-cold.
        (
            "Иргэний хуулийн дагуу гэрээ байгуулахдаа талууд эрх үүргээ тодорхой заана. "
            * 200
        ),
    ):
        t1 = time.perf_counter()
        engine.check(sample)
        record((time.perf_counter() - t1) * 1000)
    warmup_ms = (time.perf_counter() - t0) * 1000
    mark_ready(warmup_ms=warmup_ms)
    _log.info("warmup done hunspell=%s ms=%.0f", hun is not None, warmup_ms)
    return {"ok": True, "hunspell": hun is not None, "warmup_ms": round(warmup_ms)}


def _install_auto_heal() -> None:
    set_heal_handler(warm_now)


async def keep_warm_loop(stop: asyncio.Event) -> None:
    """Re-prepare the dictionary periodically. No admin action required."""
    _install_auto_heal()
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=_KEEP_WARM_SECONDS)
            break
        except asyncio.TimeoutError:
            try:
                await asyncio.to_thread(warm_now)
            except Exception:
                _log.exception("keep-warm failed")
