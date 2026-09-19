"""Apply legalinfo-derived lexicon artifacts safely (idempotent)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.engine.dictionary import _repo_root
from app.engine.hunspell_candidates import (
    _load_json,
    _load_rejected,
    _lock,
    _now,
    _save_json,
    candidates_path,
    in_curated_lexicon,
    record_admin_added,
)
from app.engine.pipeline import LanguageEngine

_log = logging.getLogger(__name__)


def trusted_path() -> Path:
    return _repo_root() / "data" / "legal_trusted.txt"


def doubt_path() -> Path:
    return _repo_root() / "data" / "legal_doubt.json"


def _read_trusted() -> list[str]:
    path = trusted_path()
    if not path.is_file():
        return []
    words: list[str] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        word = line.strip()
        folded = word.casefold()
        if len(folded) < 3 or folded in seen:
            continue
        seen.add(folded)
        words.append(folded)
    return words


def _read_doubt_items() -> list[dict[str, Any]]:
    raw = _load_json(doubt_path())
    if not isinstance(raw, dict):
        return []
    items = raw.get("items", [])
    if not isinstance(items, list):
        return []
    out: list[dict[str, Any]] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        word = str(row.get("word") or "").strip()
        folded = str(row.get("folded") or word).casefold()
        if len(folded) < 3:
            continue
        out.append(
            {
                "word": word or folded,
                "folded": folded,
                "tier": "doubt",
                "reason": str(row.get("reason") or "legalinfo · админ шалгана"),
                "suggestion": str(row.get("suggestion") or ""),
                "count": int(row.get("legal_df") or row.get("count") or 1),
                "updated_at": _now(),
                "source": "legalinfo",
            }
        )
    return out


def apply_legal_lexicon(engine: LanguageEngine) -> dict[str, Any]:
    """Merge trusted legal lemmas into curated lexicon; queue doubt for admin.

    Never auto-merges doubt. Skips words already curated or previously rejected.
    """
    dictionary = engine.dictionary
    trusted = _read_trusted()
    doubt_items = _read_doubt_items()
    rejected = _load_rejected()

    to_add = [
        word
        for word in trusted
        if word not in rejected and not in_curated_lexicon(dictionary, word)
    ]
    added = dictionary.add_words(to_add) if to_add else []
    if to_add:
        dictionary.ensure_curated(to_add)
        record_admin_added(to_add)

    queued = 0
    rows: list[dict[str, Any]] = []
    with _lock:
        raw = _load_json(candidates_path())
        existing: dict[str, dict[str, Any]] = {}
        if isinstance(raw, dict):
            for row in raw.get("items", []) if isinstance(raw.get("items"), list) else []:
                if isinstance(row, dict) and row.get("folded"):
                    existing[str(row["folded"])] = row
        for item in doubt_items:
            folded = str(item["folded"])
            if folded in rejected or in_curated_lexicon(dictionary, folded):
                continue
            prev = existing.get(folded)
            if prev:
                prev["count"] = max(int(prev.get("count") or 0), int(item.get("count") or 1))
                prev["reason"] = item["reason"]
                prev["suggestion"] = item.get("suggestion") or prev.get("suggestion") or ""
                prev["tier"] = "doubt"
                prev["updated_at"] = _now()
                prev["source"] = "legalinfo"
            else:
                existing[folded] = item
                queued += 1
        rows = sorted(
            existing.values(),
            key=lambda row: (-int(row.get("count") or 0), str(row.get("folded") or "")),
        )
        _save_json(
            candidates_path(),
            {"items": rows[:5000], "updated_at": _now()},
        )

    result = {
        "trusted_file": len(trusted),
        "doubt_file": len(doubt_items),
        "added_to_lexicon": len(added),
        "added_words": added[:50],
        "queued_for_admin": queued,
        "candidates_total": len(rows),
    }
    _log.info("legal lexicon import: %s", result)
    return result


def legal_artifacts_present() -> bool:
    return trusted_path().is_file() or doubt_path().is_file()


def legal_import_preview() -> dict[str, Any]:
    trusted = _read_trusted()
    doubt = _read_doubt_items()
    meta: dict[str, Any] = {}
    raw = _load_json(doubt_path())
    if isinstance(raw, dict):
        meta = {
            "source": raw.get("source"),
            "rules": raw.get("rules"),
            "trusted_count": raw.get("trusted_count", len(trusted)),
            "doubt_count": raw.get("doubt_count", len(doubt)),
        }
    return {
        "present": legal_artifacts_present(),
        "trusted_count": len(trusted),
        "doubt_count": len(doubt),
        "trusted_sample": trusted[:20],
        "doubt_sample": [row["word"] for row in doubt[:20]],
        "meta": meta,
    }
