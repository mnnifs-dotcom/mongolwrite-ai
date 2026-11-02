"""Unified admin review: gather words by date, preview keep/drop, confirm."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from app.engine.dictionary import DictionaryProvider
from app.engine.hunspell_candidates import (
    approve_words,
    forget_admin_added,
    in_curated_lexicon,
    list_candidates,
    record_admin_added,
    reject_words,
)
from app.engine.pending import list_pending, pop_pending_many
from app.engine.pipeline import LanguageEngine
from app.engine.runtime import get_engine
from app.engine.text import is_cyrillic_letter

_WORD_SPLIT = re.compile(r"[\s,;|]+")


def _parse_bound(value: str, *, end: bool) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        return datetime.fromisoformat(
            raw + ("T23:59:59.999999+00:00" if end else "T00:00:00+00:00")
        )
    try:
        stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=UTC)
    return stamp.astimezone(UTC)


def _in_range(stamp_raw: str, since: datetime | None, until: datetime | None) -> bool:
    if not since and not until:
        return True
    raw = (stamp_raw or "").strip()
    if not raw:
        return False
    try:
        stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return False
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=UTC)
    stamp = stamp.astimezone(UTC)
    if since and stamp < since:
        return False
    if until and stamp > until:
        return False
    return True


def _usable(word: str) -> bool:
    cleaned = word.strip()
    letters = [ch for ch in cleaned if ch.isalpha()]
    if len(cleaned) < 2 or not letters:
        return False
    return all(is_cyrillic_letter(ch) for ch in letters)


def parse_word_list(text: str) -> list[str]:
    """Split pasted/copied text into unique Cyrillic lemmas (order preserved)."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in _WORD_SPLIT.split(text or ""):
        word = raw.strip().strip("«»\"'()[]{}.,:;!?…")
        if not _usable(word):
            continue
        folded = word.casefold()
        if folded in seen:
            continue
        seen.add(folded)
        out.append(word)
    return out


def collect_review_words(
    *,
    since: str = "",
    until: str = "",
    q: str = "",
    dictionary: DictionaryProvider | None = None,
) -> dict[str, Any]:
    """Gather pending + hunspell/legal candidates not already in the curated lexicon.

    Admin-added (already-in-lexicon) words are intentionally excluded — once a word
    is in the seed, it does not belong in the review batch.
    """
    since_dt = _parse_bound(since, end=False)
    until_dt = _parse_bound(until, end=True)
    query = q.strip().casefold()
    dictionary = dictionary or get_engine().dictionary

    by_folded: dict[str, dict[str, Any]] = {}
    skipped_curated = 0

    def upsert(
        *,
        word: str,
        folded: str,
        kind: str,
        when: str,
        source: str = "",
        ref: str = "",
        extra: dict[str, Any] | None = None,
    ) -> None:
        nonlocal skipped_curated
        if not word or not folded:
            return
        if in_curated_lexicon(dictionary, word) or in_curated_lexicon(dictionary, folded):
            skipped_curated += 1
            return
        if query and query not in folded and query not in word.casefold():
            return
        if not _in_range(when, since_dt, until_dt):
            return
        row = by_folded.get(folded)
        if row is None:
            row = {
                "word": word,
                "folded": folded,
                "kinds": [],
                "sources": [],
                "when": when,
                "refs": [],
            }
            by_folded[folded] = row
        if kind and kind not in row["kinds"]:
            row["kinds"].append(kind)
        if source and source not in row["sources"]:
            row["sources"].append(source)
        if ref and ref not in row["refs"]:
            row["refs"].append(ref)
        # Keep the newest stamp visible.
        if when and when > str(row.get("when") or ""):
            row["when"] = when
        if extra:
            row.update(extra)

    for item in list_pending():
        upsert(
            word=str(item.get("word") or ""),
            folded=str(item.get("folded") or "").casefold(),
            kind="pending",
            when=str(item.get("updated_at") or ""),
            source="pending",
            extra={"rule_id": str(item.get("rule_id") or "")},
        )

    for item in list_candidates(None):
        reason = str(item.get("reason") or "")
        kind = "hunspell"
        source = "hunspell"
        if "legal" in reason.casefold() or "legalinfo" in reason.casefold():
            kind = "legalinfo"
            source = "legalinfo"
        upsert(
            word=str(item.get("word") or ""),
            folded=str(item.get("folded") or "").casefold(),
            kind=kind,
            when=str(item.get("updated_at") or item.get("seen_at") or ""),
            source=source,
            extra={
                "tier": str(item.get("tier") or ""),
                "reason": reason,
            },
        )

    items = sorted(
        by_folded.values(),
        key=lambda row: (str(row.get("when") or ""), str(row.get("folded") or "")),
        reverse=True,
    )
    words = [str(row.get("word") or "") for row in items]
    return {
        "items": items,
        "words": words,
        "count": len(items),
        "skipped_curated": skipped_curated,
        "since": since,
        "until": until,
        "text": "\n".join(words),
    }


def preview_keep_drop(
    *,
    batch_words: list[str],
    approved_text: str,
    dictionary: DictionaryProvider,
) -> dict[str, Any]:
    """Compare review batch A vs pasted keep-set B."""
    batch = parse_word_list("\n".join(batch_words))
    approved = parse_word_list(approved_text)
    batch_folded = {w.casefold(): w for w in batch}
    approved_folded = {w.casefold(): w for w in approved}

    keep = [batch_folded[f] for f in batch_folded if f in approved_folded]
    # Pasted words not in the original batch are still allowed as keep extras.
    keep_extra = [approved_folded[f] for f in approved_folded if f not in batch_folded]
    drop = [batch_folded[f] for f in batch_folded if f not in approved_folded]

    remove_from_lexicon: list[str] = []
    do_not_add: list[str] = []
    for word in drop:
        if dictionary.in_seed(word) or dictionary.contains(word):
            remove_from_lexicon.append(word)
        else:
            do_not_add.append(word)

    return {
        "batch_count": len(batch),
        "approved_count": len(approved),
        "keep": keep,
        "keep_extra": keep_extra,
        "keep_count": len(keep) + len(keep_extra),
        "drop_count": len(drop),
        "remove_from_lexicon": remove_from_lexicon,
        "do_not_add": do_not_add,
    }


def confirm_review(
    engine: LanguageEngine,
    *,
    keep: list[str],
    remove_from_lexicon: list[str],
    do_not_add: list[str],
) -> dict[str, Any]:
    """Apply the admin's final keep / drop decisions."""
    dictionary = engine.dictionary
    keep_words = parse_word_list("\n".join(keep))
    remove_words = parse_word_list("\n".join(remove_from_lexicon))
    reject_list = parse_word_list("\n".join(do_not_add))

    # 1) Keep → lexicon + clear pending; approve_words also clears hunspell queues.
    added: list[str] = []
    if keep_words:
        pop_pending_many(keep_words)
        result = approve_words(engine, keep_words)
        added = list(result.get("added") or [])
        # Ensure provenance for review keeps even if already curated.
        record_admin_added(keep_words, source="review_keep")

    # 2) Remove from lexicon (selected by admin from the preview).
    removed: list[str] = []
    if remove_words:
        removed = dictionary.remove_words(remove_words)
        if removed:
            forget_admin_added(removed)
        pop_pending_many(remove_words)
        reject_words(remove_words)

    # 3) Do-not-add: drop from pending/candidates without lexicon remove.
    rejected: list[str] = []
    if reject_list:
        pop_pending_many(reject_list)
        rejected = list(reject_words(reject_list).get("removed") or reject_list)

    return {
        "kept": keep_words,
        "kept_count": len(keep_words),
        "added_to_lexicon": added,
        "added_count": len(added),
        "removed": removed,
        "removed_count": len(removed),
        "rejected": rejected,
        "rejected_count": len(reject_list),
    }
