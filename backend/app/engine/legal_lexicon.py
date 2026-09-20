"""Auto-accept frequent legalinfo.mn spellings into the curated check lexicon."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

# Portal scrape glue — never auto-trust these.
_JUNK_FRAGMENTS = (
    "хайлт",
    "нийтлэл",
    "бүртг",
    "нэвтр",
    "имэйл",
    "портал",
    "сонордуул",
    "дэлгэрэнгүй",
    "эмхэтгэл",
    "тусламж",
    "бүртгүүл",
)

# Extra statute forms seen on legalinfo that the doubt file may miss.
_EXTRA_LEGAL = frozenset(
    {
        "садангийн",
        "номхотгох",
        "номхотгохыг",
        "номхотгоход",
        "гүйцэтгэхэд",
        "гүйцэтгэгч",
        "гүйцэтгэгчийн",
        "гүйцэтгэгчид",
        "шийдвэрийг",
        "шийдвэрийн",
    }
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _trusted_path() -> Path:
    return _repo_root() / "data" / "legal_trusted.txt"


def _doubt_path() -> Path:
    return _repo_root() / "data" / "legal_doubt.json"


def _safe_doubt_word(folded: str, legal_df: int, wiki: int) -> bool:
    if len(folded) < 3:
        return False
    if any(frag in folded for frag in _JUNK_FRAGMENTS):
        return False
    # Long glued portal noise tends to be rare on Wikipedia.
    if len(folded) > 18 and wiki < 40:
        return False
    if legal_df >= 80 and wiki >= 25:
        return True
    if legal_df >= 150 and wiki >= 15:
        return True
    return False


@lru_cache(maxsize=1)
def load_legal_auto_lexicon() -> frozenset[str]:
    """Lemmas safe to treat as correct on official legal text."""
    words: set[str] = set(_EXTRA_LEGAL)
    trusted = _trusted_path()
    if trusted.is_file():
        for line in trusted.read_text(encoding="utf-8").splitlines():
            folded = line.strip().casefold()
            if len(folded) >= 3:
                words.add(folded)
    doubt = _doubt_path()
    if doubt.is_file():
        try:
            raw = json.loads(doubt.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}
        items = raw.get("items") if isinstance(raw, dict) else None
        if isinstance(items, list):
            for row in items:
                if not isinstance(row, dict):
                    continue
                folded = str(row.get("folded") or row.get("word") or "").strip().casefold()
                try:
                    legal_df = int(row.get("legal_df") or 0)
                    wiki = int(row.get("wiki") or 0)
                except (TypeError, ValueError):
                    continue
                if _safe_doubt_word(folded, legal_df, wiki):
                    words.add(folded)
    return frozenset(words)


@lru_cache(maxsize=1)
def load_legal_frequency() -> dict[str, int]:
    """legal_df counts — boost established-spelling protection for statute forms."""
    out: dict[str, int] = {}
    doubt = _doubt_path()
    if not doubt.is_file():
        return out
    try:
        raw = json.loads(doubt.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return out
    items = raw.get("items") if isinstance(raw, dict) else None
    if not isinstance(items, list):
        return out
    for row in items:
        if not isinstance(row, dict):
            continue
        folded = str(row.get("folded") or row.get("word") or "").strip().casefold()
        if len(folded) < 3:
            continue
        try:
            legal_df = int(row.get("legal_df") or 0)
        except (TypeError, ValueError):
            continue
        if legal_df > 0:
            out[folded] = max(out.get(folded, 0), legal_df)
    return out
