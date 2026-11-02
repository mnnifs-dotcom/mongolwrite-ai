"""Apply legalinfo-derived lexicon artifacts safely (idempotent)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.engine.dictionary import _repo_root
from app.engine.hunspell_candidates import (
    _load_json,
    _load_rejected,
    _load_rows,
    _lock,
    _now,
    _save_rows,
    in_curated_lexicon,
    queue_review_words,
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
        stamped = _now()
        out.append(
            {
                "word": word or folded,
                "folded": folded,
                "tier": "doubt",
                "reason": str(row.get("reason") or "legalinfo · админ шалгана"),
                "suggestion": str(row.get("suggestion") or ""),
                "count": max(1, int(row.get("legal_df") or row.get("count") or 1)),
                "seen_at": stamped,
                "updated_at": stamped,
            }
        )
    return out


def apply_legal_lexicon(engine: LanguageEngine) -> dict[str, Any]:
    """Queue trusted + doubt legal lemmas for admin review (no lexicon write).

    Never auto-merges into the curated seed. Skips words already curated or
    previously rejected. Lexicon membership happens only via «Шалгах багц».
    """
    dictionary = engine.dictionary
    trusted = _read_trusted()
    doubt_items = _read_doubt_items()
    rejected = _load_rejected()

    trusted_queue = [
        word
        for word in trusted
        if word not in rejected and not in_curated_lexicon(dictionary, word)
    ]
    trusted_result = queue_review_words(
        trusted_queue,
        reason="legalinfo · trusted файл · шалгах багцад",
        tier="reliable",
        dictionary=dictionary,
        skip_curated=True,
    )

    queued = int(trusted_result.get("queued_count") or 0)
    with _lock:
        existing = _load_rows()
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
            else:
                existing[folded] = item
                queued += 1
        _save_rows(existing)
        total = len(existing)

    result = {
        "trusted_file": len(trusted),
        "doubt_file": len(doubt_items),
        "added_to_lexicon": 0,
        "added_words": [],
        "queued_trusted": int(trusted_result.get("queued_count") or 0),
        "queued_for_admin": queued,
        "candidates_total": total,
    }
    _log.info("legal lexicon import (review-only): %s", result)
    return result


def legal_artifacts_present() -> bool:
    return trusted_path().is_file() or doubt_path().is_file()


def legal_import_preview() -> dict[str, Any]:
    trusted = _read_trusted()
    doubt = _read_doubt_items()
    meta: dict[str, Any] = {}
    corpus: dict[str, Any] = {}
    raw = _load_json(doubt_path())
    if isinstance(raw, dict):
        corpus_raw = raw.get("corpus")
        if isinstance(corpus_raw, dict):
            corpus = {
                "articles": int(corpus_raw.get("articles") or 0),
                "unique_tokens": int(corpus_raw.get("unique_tokens") or 0),
                "already_in_seed": int(corpus_raw.get("already_in_seed") or 0),
            }
        meta = {
            "source": raw.get("source"),
            "rules": raw.get("rules"),
            "trusted_count": raw.get("trusted_count", len(trusted)),
            "doubt_count": raw.get("doubt_count", len(doubt)),
            "corpus": corpus,
        }
    return {
        "present": legal_artifacts_present(),
        "trusted_count": len(trusted),
        "doubt_count": len(doubt),
        "trusted_sample": trusted[:20],
        "doubt_sample": [row["word"] for row in doubt[:20]],
        "corpus": corpus,
        "meta": meta,
    }
