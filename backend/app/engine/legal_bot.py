"""Background bot: ingest one legalinfo.mn law every 20–40 minutes."""

from __future__ import annotations

import asyncio
import logging
import random
import threading
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings
from app.engine.legal_laws import ingest_law, peek_next_law_id
from app.engine.runtime import get_engine

_log = logging.getLogger(__name__)
_status_lock = threading.Lock()
_status: dict[str, Any] = {
    "enabled": True,
    "running": False,
    "last_started_at": "",
    "last_finished_at": "",
    "last_law_id": "",
    "last_title": "",
    "last_ok": None,
    "last_error": "",
    "last_added": 0,
    "last_queued": 0,
    "next_wait_seconds": 0,
    "cycles": 0,
}


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def bot_status() -> dict[str, Any]:
    with _status_lock:
        return {
            **_status,
            "enabled": bool(settings.legal_ingest_bot),
            "min_interval_seconds": int(settings.legal_ingest_min_seconds),
            "max_interval_seconds": int(settings.legal_ingest_max_seconds),
        }


def _set_status(**kwargs: Any) -> None:
    with _status_lock:
        _status.update(kwargs)


def ingest_next_law_once() -> dict[str, Any]:
    """Pick the next pending law and ingest it (or no-op if queue empty)."""
    law_id = peek_next_law_id()
    if not law_id:
        return {"ok": True, "empty": True, "law_id": None}
    engine = get_engine()
    result = ingest_law(engine, law_id, source="legal_bot")
    return {"ok": True, "empty": False, **result}


def _pick_wait_seconds() -> int:
    low = max(60, int(settings.legal_ingest_min_seconds))
    high = max(low, int(settings.legal_ingest_max_seconds))
    return random.randint(low, high)


async def legal_ingest_loop(stop: asyncio.Event) -> None:
    """Ingest one law every 20–40 minutes while the app is up."""
    if not settings.legal_ingest_bot:
        _log.info("legal ingest bot disabled")
        _set_status(enabled=False, running=False)
        return

    _set_status(enabled=True, running=True)
    _log.info(
        "legal ingest bot started interval=%s-%ss",
        settings.legal_ingest_min_seconds,
        settings.legal_ingest_max_seconds,
    )

    # Small startup delay so warm-up finishes first.
    try:
        await asyncio.wait_for(stop.wait(), timeout=45)
        return
    except asyncio.TimeoutError:
        pass

    while not stop.is_set():
        wait_s = _pick_wait_seconds()
        _set_status(next_wait_seconds=wait_s)
        try:
            await asyncio.wait_for(stop.wait(), timeout=wait_s)
            break
        except asyncio.TimeoutError:
            pass

        _set_status(last_started_at=_now(), last_error="", running=True)
        try:
            result = await asyncio.to_thread(ingest_next_law_once)
            if result.get("empty"):
                _set_status(
                    last_finished_at=_now(),
                    last_ok=True,
                    last_law_id="",
                    last_title="",
                    last_added=0,
                    last_queued=0,
                    last_error="Үлдсэн хууль алга",
                    cycles=int(_status.get("cycles") or 0) + 1,
                )
                _log.info("legal bot: queue empty")
            else:
                _set_status(
                    last_finished_at=_now(),
                    last_ok=True,
                    last_law_id=str(result.get("law_id") or ""),
                    last_title=str(result.get("title") or ""),
                    last_added=int(result.get("added_to_lexicon") or 0),
                    last_queued=int(result.get("queued_candidates") or 0),
                    last_error="",
                    cycles=int(_status.get("cycles") or 0) + 1,
                )
                _log.info(
                    "legal bot ingested lawId=%s added=%s",
                    result.get("law_id"),
                    result.get("added_to_lexicon"),
                )
        except Exception as exc:
            _set_status(
                last_finished_at=_now(),
                last_ok=False,
                last_error=str(exc)[:400],
                cycles=int(_status.get("cycles") or 0) + 1,
            )
            _log.exception("legal bot ingest failed")

    _set_status(running=False)
