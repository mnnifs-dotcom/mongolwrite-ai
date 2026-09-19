from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from app.engine.confusables import _variants
from app.engine.dictionary import DictionaryProvider, _FREQ_TRUST, _repo_root
from app.engine.grammar import _glued_forms
from app.engine.misspellings import lookup_misspelling
from app.engine.pipeline import LanguageEngine
from app.engine.spelling import _RULE_FIRST, _is_implausible, _suggest
from app.engine.text import is_cyrillic_letter, tokenize

Tier = Literal["reliable", "doubt"]

# Clear orthography/grammar hits — admin should not review these one-by-one.
_CLEAR_RULES = _RULE_FIRST | {
    "common_misspelling",
    "doubled_letter",
    "glued_auxiliary",
    "glued_question_particle",
    "glued_directive",
    "glued_words",
    "separate_particle",
}

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


def admin_added_path() -> Path:
    return persist_dir() / "admin_added.json"


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


def _load_admin_added() -> list[dict[str, Any]]:
    raw = _load_json(admin_added_path())
    rows = raw.get("words", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
    out: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if isinstance(row, str):
            word = row.strip()
            if len(word) < 2:
                continue
            out.append({"word": word, "folded": word.casefold(), "added_at": ""})
            continue
        if not isinstance(row, dict):
            continue
        word = str(row.get("word") or "").strip()
        folded = str(row.get("folded") or word).casefold()
        if len(folded) < 2:
            continue
        out.append(
            {
                "word": word or folded,
                "folded": folded,
                "added_at": str(row.get("added_at") or ""),
            }
        )
    return out


def _save_admin_added(rows: list[dict[str, Any]]) -> None:
    _save_json(admin_added_path(), {"words": rows[: _MAX_CANDIDATES]})


def record_admin_added(words: list[str]) -> list[dict[str, Any]]:
    """Prepend newly admin-approved words (newest first)."""
    stamped = _now()
    with _lock:
        rows = _load_admin_added()
        existing = {str(row.get("folded") or "") for row in rows}
        prepend: list[dict[str, Any]] = []
        for raw in words:
            word = raw.strip()
            folded = word.casefold()
            if len(folded) < 2:
                continue
            if folded in existing:
                rows = [row for row in rows if row.get("folded") != folded]
            prepend.append({"word": word, "folded": folded, "added_at": stamped})
            existing.add(folded)
        merged = prepend + rows
        _save_admin_added(merged)
        return prepend


def forget_admin_added(words: list[str]) -> list[str]:
    """Drop lemmas from the admin-added log (after lexicon remove)."""
    targets = {raw.strip().casefold() for raw in words if raw.strip()}
    if not targets:
        return []
    with _lock:
        rows = _load_admin_added()
        kept: list[dict[str, Any]] = []
        dropped: list[str] = []
        for row in rows:
            folded = str(row.get("folded") or "").casefold()
            if folded in targets:
                dropped.append(str(row.get("word") or folded))
                continue
            kept.append(row)
        if dropped:
            _save_admin_added(kept)
        return dropped


def _parse_day_bound(value: str, *, end: bool) -> datetime | None:
    """Parse YYYY-MM-DD (or full ISO) into an inclusive UTC bound."""
    raw = (value or "").strip()
    if not raw:
        return None
    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        stamp = datetime.fromisoformat(raw + ("T23:59:59.999999+00:00" if end else "T00:00:00+00:00"))
        return stamp
    try:
        stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=UTC)
    return stamp.astimezone(UTC)


def list_admin_added(
    *,
    since: str = "",
    until: str = "",
    q: str = "",
) -> list[dict[str, Any]]:
    """Admin-added + user-dictionary words, newest first. Optional date/query filter."""
    from app.engine.dictionary import list_user_dictionary_lemmas

    with _lock:
        logged = list(_load_admin_added())
    by_folded = {str(row.get("folded") or ""): row for row in logged if row.get("folded")}
    # Prepend file lemmas that are missing from the admin log (older adds).
    for lemma in list_user_dictionary_lemmas():
        if lemma in by_folded:
            continue
        by_folded[lemma] = {"word": lemma, "folded": lemma, "added_at": ""}
        logged.append(by_folded[lemma])
    # Keep logged order (newest first), then any file-only lemmas already appended.
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in logged:
        folded = str(row.get("folded") or "")
        if not folded or folded in seen:
            continue
        seen.add(folded)
        out.append(row)

    since_dt = _parse_day_bound(since, end=False)
    until_dt = _parse_day_bound(until, end=True)
    query = q.strip().casefold()
    if not since_dt and not until_dt and not query:
        return out

    filtered: list[dict[str, Any]] = []
    for row in out:
        word = str(row.get("word") or "")
        folded = str(row.get("folded") or word).casefold()
        if query and query not in folded and query not in word.casefold():
            continue
        added_raw = str(row.get("added_at") or "").strip()
        if since_dt or until_dt:
            if not added_raw:
                # File-only lemmas have no stamp — hide when a date range is set.
                continue
            try:
                added_dt = datetime.fromisoformat(added_raw.replace("Z", "+00:00"))
            except ValueError:
                continue
            if added_dt.tzinfo is None:
                added_dt = added_dt.replace(tzinfo=UTC)
            added_dt = added_dt.astimezone(UTC)
            if since_dt and added_dt < since_dt:
                continue
            if until_dt and added_dt > until_dt:
                continue
        filtered.append(row)
    return filtered


def admin_lists_payload() -> dict[str, Any]:
    """Single payload for the admin UI lists."""
    prune_clear_error_candidates()
    reliable = list_candidates("reliable")
    doubt = list_candidates("doubt")
    added = list_admin_added()
    return {
        "reliable": reliable,
        "doubt": doubt,
        "added": added,
        "counts": {
            "reliable": len(reliable),
            "doubt": len(doubt),
            "added": len(added),
            "total": len(reliable) + len(doubt),
        },
    }


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
    """True when the word is already in the curated seed/user list (not Hunspell-only)."""
    return dictionary.in_seed(word)


def is_clear_orthography_error(dictionary: DictionaryProvider, word: str) -> bool:
    """True for glued/rule misspellings that the engine can already fix automatically."""
    cleaned = word.strip()
    if len(cleaned) < 2:
        return False
    if lookup_misspelling(cleaned):
        return True
    tokens = tokenize(cleaned)
    for item in _glued_forms(tokens, dictionary):
        if item.rule_id in _CLEAR_RULES:
            return True
    if len(cleaned) >= 4:
        suggested = _suggest(cleaned, dictionary)
        if suggested and suggested[1] in _CLEAR_RULES:
            return True
    return False


def classify_candidate(dictionary: DictionaryProvider, word: str) -> dict[str, Any] | None:
    """Return reliable/doubt item, or None when the word should not be listed.

    Only uncertain lexicon gaps belong here — clear rule/grammar errors are excluded
    so admins are not asked to re-judge every obvious misspelling.
    """
    cleaned = word.strip()
    folded = cleaned.casefold()
    if len(folded) < 2:
        return None
    if lookup_misspelling(cleaned):
        return None
    if _is_implausible(cleaned):
        return None
    if in_curated_lexicon(dictionary, cleaned):
        return None
    if is_clear_orthography_error(dictionary, cleaned):
        return None

    hun_ok = hunspell_knows(dictionary, cleaned)
    wiki = dictionary.wiki_frequency(cleaned)
    better = ""
    better_wiki = 0
    for variant in _variants(cleaned, limit=16):
        vwiki = dictionary.wiki_frequency(variant)
        known = dictionary.in_seed(variant) or dictionary.in_wordlist(variant)
        if (known or vwiki >= _FREQ_TRUST) and vwiki > wiki + 20:
            if vwiki > better_wiki:
                better = variant
                better_wiki = vwiki

    if better:
        return {
            "word": cleaned,
            "folded": folded,
            "tier": "doubt",
            "reason": f"«{better}» илүү түгээмэл. Зөв үү, буруу юу?",
            "suggestion": better,
        }
    if hun_ok and wiki >= _FREQ_TRUST:
        return {
            "word": cleaned,
            "folded": folded,
            "tier": "reliable",
            "reason": "Hunspell зөвшөөрсөн · Википедиа дээр түгээмэл.",
            "suggestion": "",
        }
    if hun_ok:
        return {
            "word": cleaned,
            "folded": folded,
            "tier": "doubt",
            "reason": "Hunspell зөвшөөрсөн боловч давтамж бага. Админ шалгана.",
            "suggestion": "",
        }
    return {
        "word": cleaned,
        "folded": folded,
        "tier": "doubt",
        "reason": "Эргэлзээтэй / санд байхгүй үг. Админ шийдэнэ.",
        "suggestion": "",
    }


def extract_missing_words(engine: LanguageEngine, text: str) -> list[str]:
    """Cyrillic tokens missing from the curated lexicon (Hunspell-only or unknown)."""
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
        found.append(token.text)
    return found


def extract_hunspell_only(engine: LanguageEngine, text: str) -> list[str]:
    """Backward-compatible alias — now returns all curated-missing words."""
    return extract_missing_words(engine, text)


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
    """Harvest curated-missing words from text into candidate lists. Returns queued count."""
    if not text.strip():
        return 0
    words = extract_missing_words(engine, text)
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


def prune_clear_error_candidates(dictionary: DictionaryProvider | None = None) -> int:
    """Drop queued words that are clear orthography/grammar errors (one-shot cleanup)."""
    from app.engine.runtime import get_engine

    dict_provider = dictionary or get_engine().dictionary
    removed = 0
    with _lock:
        rows = _load_rows()
        drop = [
            folded
            for folded, row in rows.items()
            if is_clear_orthography_error(dict_provider, str(row.get("word") or folded))
        ]
        if not drop:
            return 0
        for folded in drop:
            rows.pop(folded, None)
            removed += 1
        _save_rows(rows)
    return removed


def counts() -> dict[str, int]:
    rows = list_candidates()
    reliable = sum(1 for row in rows if row.get("tier") == "reliable")
    doubt = sum(1 for row in rows if row.get("tier") == "doubt")
    return {"reliable": reliable, "doubt": doubt, "total": len(rows)}


def approve_words(engine: LanguageEngine, words: list[str]) -> dict[str, Any]:
    folded_wanted = {item.strip().casefold() for item in words if item.strip()}
    if not folded_wanted:
        return {"added": [], "added_count": 0, "recorded": []}
    with _lock:
        rows = _load_rows()
        to_add: list[str] = []
        for folded in list(folded_wanted):
            row = rows.pop(folded, None)
            if row:
                to_add.append(str(row.get("word") or folded))
            else:
                to_add.append(folded)
        # Persist candidates removal first so a crash mid-add does not re-show them forever.
        _save_rows(rows)

    # Add outside the candidates lock — dictionary has its own locking needs.
    added = engine.dictionary.add_words(to_add)
    # Force curated seed even when the form was already known via expansions/Hunspell cache.
    ensured = engine.dictionary.ensure_curated(to_add)
    recorded_words = list(dict.fromkeys([*added, *ensured, *[w.casefold() for w in to_add]]))
    recorded = record_admin_added(to_add)
    return {
        "added": added or ensured,
        "added_count": len(added) if added else len(ensured),
        "recorded": recorded,
        "recorded_count": len(recorded),
        "words": recorded_words,
    }


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


def queue_doubt_words(
    words: list[str],
    *,
    reason: str = "Админ сангаас хассан · алдаатай гэж тэмдэглэсэн",
) -> dict[str, Any]:
    """Put lemmas into the admin doubt queue (and clear any prior rejection)."""
    cleaned = [item.strip() for item in words if item.strip()]
    if not cleaned:
        return {"queued": [], "queued_count": 0}
    stamped = _now()
    queued: list[str] = []
    with _lock:
        rows = _load_rows()
        rejected = _load_rejected()
        for word in cleaned:
            folded = word.casefold()
            rejected.discard(folded)
            prev = rows.get(folded)
            if prev:
                prev["tier"] = "doubt"
                prev["reason"] = reason
                prev["updated_at"] = stamped
                prev["count"] = max(1, int(prev.get("count") or 1))
            else:
                rows[folded] = {
                    "word": word,
                    "folded": folded,
                    "tier": "doubt",
                    "reason": reason,
                    "suggestion": "",
                    "count": 1,
                    "seen_at": stamped,
                    "updated_at": stamped,
                }
            queued.append(folded)
        # Cap growth
        if len(rows) > _MAX_CANDIDATES:
            ordered = sorted(
                rows.values(),
                key=lambda row: str(row.get("updated_at") or ""),
                reverse=True,
            )[:_MAX_CANDIDATES]
            rows = {str(row["folded"]): row for row in ordered}
        _save_rows(rows)
        _save_rejected(rejected)
    return {"queued": queued, "queued_count": len(queued)}


def harvest_safe(engine: LanguageEngine, text: str) -> None:
    """Best-effort harvest for check path — never raises."""
    try:
        record_from_text(engine, text)
    except Exception:
        _log.exception("hunspell candidate harvest failed")
