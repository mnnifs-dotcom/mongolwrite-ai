from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.engine.dictionary import persist_dir
from app.engine.text import is_cyrillic_letter

_lock = threading.Lock()


def pending_path() -> Path:
    return persist_dir() / "pending_skipped.json"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _load(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(raw, dict):
        raw = raw.get("words", [])
    if not isinstance(raw, list):
        return []
    items: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        word = str(row.get("word") or "").strip()
        folded = str(row.get("folded") or word).casefold()
        if not word or not folded:
            continue
        items.append(
            {
                "word": word,
                "folded": folded,
                "rule_id": str(row.get("rule_id") or ""),
                "count": max(1, int(row.get("count") or 1)),
                "updated_at": str(row.get("updated_at") or _now()),
            }
        )
    return items


def _save(path: Path, items: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"words": items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _usable_word(word: str) -> bool:
    letters = [ch for ch in word if ch.isalpha()]
    if len(word) < 2 or not letters:
        return False
    return all(is_cyrillic_letter(ch) for ch in letters)


def record_skip(word: str, rule_id: str = "") -> bool:
    cleaned = word.strip()
    if not _usable_word(cleaned):
        return False
    folded = cleaned.casefold()
    path = pending_path()
    with _lock:
        items = _load(path)
        for item in items:
            if item["folded"] == folded:
                item["count"] = int(item["count"]) + 1
                item["updated_at"] = _now()
                if rule_id:
                    item["rule_id"] = rule_id
                _save(path, items)
                return True
        items.append(
            {
                "word": cleaned,
                "folded": folded,
                "rule_id": rule_id,
                "count": 1,
                "updated_at": _now(),
            }
        )
        _save(path, items)
        return True


def list_pending() -> list[dict[str, Any]]:
    with _lock:
        items = _load(pending_path())
    return sorted(items, key=lambda row: (-int(row["count"]), str(row["folded"])))


def pop_pending(folded: str) -> dict[str, Any] | None:
    key = folded.casefold().strip()
    path = pending_path()
    with _lock:
        items = _load(path)
        found: dict[str, Any] | None = None
        kept: list[dict[str, Any]] = []
        for item in items:
            if item["folded"] == key and found is None:
                found = item
            else:
                kept.append(item)
        if found is not None:
            _save(path, kept)
        return found
