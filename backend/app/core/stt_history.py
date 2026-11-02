"""Per-user speech→text history (text only — never audio)."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.engine.dictionary import persist_dir

_lock = threading.Lock()
_MAX_ITEMS = 80
_MAX_TEXT = 200_000


def _path(user_id: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in (user_id or "")[:80])
    return persist_dir() / "stt_history" / f"{safe or 'unknown'}.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(user_id: str) -> list[dict[str, Any]]:
    path = _path(user_id)
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = raw.get("items") if isinstance(raw, dict) else None
    if not isinstance(items, list):
        return []
    return [row for row in items if isinstance(row, dict)]


def _save(user_id: str, items: list[dict[str, Any]]) -> None:
    path = _path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"items": items[:_MAX_ITEMS]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_transcript(
    user_id: str,
    *,
    transcription: str,
    filename: str = "",
    duration_seconds: float = 0.0,
    amount_mnt: float = 0.0,
    order_id: str = "",
    chimege_uuid: str = "",
) -> dict[str, Any] | None:
    uid = (user_id or "").strip()
    text = (transcription or "").strip()[:_MAX_TEXT]
    if not uid or not text:
        return None
    row = {
        "id": str(uuid.uuid4()),
        "filename": (filename or "")[:120],
        "transcription": text,
        "duration_seconds": round(float(duration_seconds or 0), 2),
        "amount_mnt": int(amount_mnt or 0),
        "order_id": (order_id or "")[:80],
        "chimege_uuid": (chimege_uuid or "")[:80],
        "created_at": _now(),
    }
    with _lock:
        items = _load(uid)
        # Idempotent if the same order already saved.
        if row["order_id"]:
            for existing in items:
                if str(existing.get("order_id") or "") == row["order_id"]:
                    existing["transcription"] = text
                    existing["duration_seconds"] = row["duration_seconds"]
                    _save(uid, items)
                    return dict(existing)
        items.insert(0, row)
        _save(uid, items)
        return dict(row)


def list_transcripts(user_id: str) -> list[dict[str, Any]]:
    uid = (user_id or "").strip()
    if not uid:
        return []
    with _lock:
        items = _load(uid)
    out: list[dict[str, Any]] = []
    for row in items:
        text = str(row.get("transcription") or "")
        out.append(
            {
                "id": row.get("id", ""),
                "filename": row.get("filename", ""),
                "duration_seconds": row.get("duration_seconds", 0),
                "amount_mnt": row.get("amount_mnt", 0),
                "created_at": row.get("created_at", ""),
                "preview": text[:160],
            }
        )
    return out


def get_transcript(user_id: str, item_id: str) -> dict[str, Any] | None:
    uid = (user_id or "").strip()
    needle = (item_id or "").strip()
    if not uid or not needle:
        return None
    with _lock:
        for row in _load(uid):
            if str(row.get("id") or "") == needle:
                return dict(row)
    return None
