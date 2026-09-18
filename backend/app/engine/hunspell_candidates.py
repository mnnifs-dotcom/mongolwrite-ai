from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from app.engine.confusables import _variants
from app.engine.dictionary import DictionaryProvider, _FREQ_TRUST, _repo_root
from app.engine.misspellings import lookup_misspelling
from app.engine.pipeline import LanguageEngine
from app.engine.spelling import _is_implausible
from app.engine.text import is_cyrillic_letter, tokenize

Tier = Literal["reliable", "doubt"]

_log = logging.getLogger(__name__)
_lock = threading.Lock()
_MAX_CANDIDATES = 5_000

# In-memory buffer so checks stay fast; flushed under lock.
_pending_bump: dict[str, dict[str, Any]] = {}


def persist_dir() -> Path:
    return _repo_root() / "data" / "persist"


def candidates_path() -> Path:
    return persist_dir() / "hunspell_candidates.json"


def rejected_path() -> Path:
    return persist_dir() / "hunspell_rejected.json"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_rejected() -> set[str]:
    raw = _load_json(rejected_path())
    if isinstance(raw, dict):
        words = raw.get("words", [])
    else:
        words = raw if isinstance(raw, list) else []
    return {str(item).casefold() for item in words if str(item).strip()}


def _save_rejected(words: set[str]) -> None:
    _save_json(rejected_path(), {"words": sorted(words)})


def _load_rows() -> dict[str, dict[str, Any]]:
    raw = _load_json(candidates_path())
    rows = raw.get("words", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        folded = str(row.get("folded") or row.get("word") or "").strip().casefold()
        if len(folded) < 2:
            continue
        out[folded] = {
            "word": str(row.get("word") or folded).strip() or folded,
            "folded": folded,
            "tier": str(row.get("tier") or "doubt"),
            "reason": str(row.get("reason") or ""),
            "suggestion": str(row.get("suggestion") or ""),
            "count": max(1, int(row.get("count") or 1)),
            "seen_at": str(row.get("seen_at") or _now()),
            "updated_at": str(row.get("updated_at") or row.get("seen_at") or _now()),
        }
    return out


def _save_rows(rows: dict[str, dict[str, Any]]) -> None:
    items = sorted(rows.values(), key=lambda row: (-int(row["count"]), row["folded"]))
    if len(items) > _MAX_CANDIDATES:
        items = items[:_MAX_CANDIDATES]
    _save_json(candidates_path(), {"words": items})


def hunspell_knows(dictionary: DictionaryProvider, word: str) -> bool:
    method = getattr(dictionary, "hunspell_knows", None)
    if callable(method):
        return bool(method(word))
    hun = getattr(dictionary, "_hunspell", None)
    if hun is None:
        return False
    folded = word.casefold()
    return bool(hun.lookup(folded) or hun.lookup(word))


def in_curated_lexicon(dictionary: DictionaryProvider, word: str) -> bool:
    """True when the word is already in the seed/user curated list."""
    return dictionary.in_seed(word) or dictionary.in_wordlist(word)


def classify_candidate(dictionary: DictionaryProvider, word: str) -> dict[str, Any] | None:
    """Return reliable/doubt item, or None when the word should not be listed."""
    cleaned = word.strip()
    folded = cleaned.casefold()
    if len(folded) < 2:
        return None
    miss = lookup_misspelling(cleaned)
    if miss:
        return None
    if _is_implausible(cleaned):
        return None
    if not hunspell_knows(dictionary, cleaned):
        return None
    if in_curated_lexicon(dictionary, cleaned):
        return None

    wiki = dictionary.wiki_frequency(cleaned)
    better = ""
    better_wiki = 0
    for variant in _variants(cleaned, limit=16):
        vwiki = dictionary.wiki_frequency(variant)
        known = dictionary.in_wordlist(variant) or dictionary.in_seed(variant)
        if (known or vwiki >= _FREQ_TRUST) and vwiki > wiki + 20:
            if vwiki > better_wiki:
                better = variant
                better_wiki = vwiki

    if better:
        return {
            "word": cleaned,
            "folded": folded,
            "tier": "doubt",
            "reason": f"«{better}» илүү түгээмэл. Hunspell зөв гэсэн ч эргэлзээтэй.",
            "suggestion": better,
        }
    if wiki >= _FREQ_TRUST:
        return {
            "word": cleaned,
            "folded": folded,
            "tier": "reliable",
            "reason": "Hunspell зөвшөөрсөн · Википедиа дээр түгээмэл.",
            "suggestion": "",
        }
    return {
        "word": cleaned,
        "folded": folded,
        "tier": "doubt",
        "reason": "Hunspell зөвшөөрсөн боловч давтамж бага. Админ шалгана.",
        "suggestion": "",
    }


def extract_hunspell_only(engine: LanguageEngine, text: str) -> list[str]:
    dictionary = engine.dictionary
    found: list[str] = []
    seen: set[str] = set()
    for token in tokenize(text):
        letters = [ch for ch in token.text if ch.isalpha()]
        if len(token.text) < 2 or not letters:
            continue
        if not all(is_cyrillic_letter(ch) for ch in letters):
            continue
        folded = token.text.casefold()
        if folded in seen:
            continue
        seen.add(folded)
        if in_curated_lexicon(dictionary, folded):
            continue
        if not hunspell_knows(dictionary, token.text):
            continue
        found.append(token.text)
    return found


def _flush_pending() -> int:
    global _pending_bump
    with _lock:
        bumps = _pending_bump
        _pending_bump = {}
        if not bumps:
            return 0
        rejected = _load_rejected()
        rows = _load_rows()
        changed = 0
        for folded, payload in bumps.items():
            if folded in rejected:
                continue
            item = payload["classified"]
            if item is None:
                continue
            existing = rows.get(folded)
            stamped = _now()
            if existing:
                existing["count"] = int(existing["count"]) + int(payload["count"])
                existing["tier"] = item["tier"]
                existing["reason"] = item["reason"]
                existing["suggestion"] = item["suggestion"]
                existing["updated_at"] = stamped
                if len(payload["word"]) >= len(str(existing["word"])):
                    existing["word"] = payload["word"]
            else:
                rows[folded] = {
                    "word": payload["word"],
                    "folded": folded,
                    "tier": item["tier"],
                    "reason": item["reason"],
                    "suggestion": item["suggestion"],
                    "count": int(payload["count"]),
                    "seen_at": stamped,
                    "updated_at": stamped,
                }
            changed += 1
        if changed:
            _save_rows(rows)
        return changed


def record_from_text(engine: LanguageEngine, text: str) -> int:
    """Harvest Hunspell-only words from text into candidate lists. Returns queued count."""
    if not text.strip() or not engine.dictionary.has_hunspell:
        return 0
    words = extract_hunspell_only(engine, text)
    if not words:
        return 0
    dictionary = engine.dictionary
    with _lock:
        rejected = _load_rejected()
        for word in words:
            folded = word.casefold()
            if folded in rejected:
                continue
            classified = classify_candidate(dictionary, word)
            if classified is None:
                continue
            bump = _pending_bump.get(folded)
            if bump:
                bump["count"] += 1
                bump["word"] = word
                bump["classified"] = classified
            else:
                _pending_bump[folded] = {
                    "word": word,
                    "count": 1,
                    "classified": classified,
                }
    return _flush_pending()


def list_candidates(tier: Tier | str | None = None) -> list[dict[str, Any]]:
    _flush_pending()
    with _lock:
        rows = list(_load_rows().values())
    if tier in {"reliable", "doubt"}:
        rows = [row for row in rows if row.get("tier") == tier]
    rows.sort(key=lambda row: (-int(row.get("count") or 1), str(row.get("folded") or "")))
    return rows


def counts() -> dict[str, int]:
    rows = list_candidates()
    reliable = sum(1 for row in rows if row.get("tier") == "reliable")
    doubt = sum(1 for row in rows if row.get("tier") == "doubt")
    return {"reliable": reliable, "doubt": doubt, "total": len(rows)}


def approve_words(engine: LanguageEngine, words: list[str]) -> dict[str, Any]:
    folded_wanted = {item.strip().casefold() for item in words if item.strip()}
    if not folded_wanted:
        return {"added": [], "added_count": 0}
    with _lock:
        rows = _load_rows()
        to_add: list[str] = []
        for folded in list(folded_wanted):
            row = rows.pop(folded, None)
            if row:
                to_add.append(str(row.get("word") or folded))
            else:
                to_add.append(folded)
        added = engine.dictionary.add_words(to_add)
        _save_rows(rows)
    return {"added": added, "added_count": len(added)}


def reject_words(words: list[str]) -> dict[str, Any]:
    folded_wanted = {item.strip().casefold() for item in words if item.strip()}
    if not folded_wanted:
        return {"removed": [], "removed_count": 0}
    with _lock:
        rows = _load_rows()
        rejected = _load_rejected()
        removed: list[str] = []
        for folded in folded_wanted:
            row = rows.pop(folded, None)
            rejected.add(folded)
            removed.append(str(row["word"]) if row else folded)
        _save_rows(rows)
        _save_rejected(rejected)
    return {"removed": removed, "removed_count": len(removed)}


def harvest_safe(engine: LanguageEngine, text: str) -> None:
    """Best-effort harvest for check path — never raises."""
    try:
        record_from_text(engine, text)
    except Exception:
        _log.exception("hunspell candidate harvest failed")
