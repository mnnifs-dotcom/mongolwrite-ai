"""Persisted user feedback / error reports (volume JSON)."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.engine.dictionary import persist_dir

_lock = threading.Lock()
_MAX_ITEMS = 5_000

ALLOWED_CATEGORIES = frozenset({"spelling", "bichig", "site", "other"})


def _path() -> Path:
    return persist_dir() / "feedback.json"


def _load() -> list[dict[str, Any]]:
    path = _path()
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


def _save(items: list[dict[str, Any]]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"items": items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_feedback(
    *,
    category: str,
    message: str,
    word: str = "",
    email: str = "",
    page: str = "",
) -> dict[str, Any]:
    cat = (category or "other").strip().lower()
    if cat not in ALLOWED_CATEGORIES:
        cat = "other"
    text = (message or "").strip()
    if len(text) < 8:
        raise ValueError("message_too_short")
    if len(text) > 4000:
        text = text[:4000]
    row = {
        "id": str(uuid.uuid4()),
        "category": cat,
        "word": (word or "").strip()[:200],
        "message": text,
        "email": (email or "").strip()[:200],
        "page": (page or "").strip()[:200],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        items = _load()
        items.insert(0, row)
        if len(items) > _MAX_ITEMS:
            items = items[:_MAX_ITEMS]
        _save(items)
    return dict(row)


def list_feedback(*, limit: int = 100) -> list[dict[str, Any]]:
    cap = max(1, min(int(limit), 500))
    with _lock:
        return [dict(row) for row in _load()[:cap]]
