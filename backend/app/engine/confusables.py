from __future__ import annotations

import uuid

from app.engine.dictionary import DictionaryProvider
from app.engine.models import Category, Correction, Severity, Source
from app.engine.text import Token

PAIRS = (
    ("о", "ө"),
    ("ө", "о"),
    ("у", "ү"),
    ("ү", "у"),
    ("О", "Ө"),
    ("Ө", "О"),
    ("У", "Ү"),
    ("Ү", "У"),
)

_CONFUSABLE_CHARS = frozenset("оөуүОӨУҮ")


def _variants(word: str, limit: int = 32) -> list[str]:
    indexes = [i for i, ch in enumerate(word) if ch in _CONFUSABLE_CHARS]
    if not indexes or len(indexes) > 6:
        return []
    out: list[str] = []
    max_bits = min(1 << len(indexes), 64)
    for bits in range(1, max_bits):
        chars = list(word)
        flipped = 0
        for n, idx in enumerate(indexes):
            if bits & (1 << n):
                ch = chars[idx]
                for a, b in PAIRS:
                    if ch == a:
                        chars[idx] = b
                        flipped += 1
                        break
        if flipped:
            out.append("".join(chars))
    unique: list[str] = []
    seen: set[str] = set()
    for item in sorted(set(out), key=lambda w: sum(a != b for a, b in zip(word, w, strict=True))):
        if item not in seen and item != word:
            seen.add(item)
            unique.append(item)
        if len(unique) >= limit:
            break
    return unique


def check_confusables(tokens: list[Token], dictionary: DictionaryProvider) -> list[Correction]:
    corrections: list[Correction] = []
    # Long docs: only inspect tokens that can flip о/ө у/ү, and cache lookups.
    known_cache: dict[str, bool] = {}
    checked: set[str] = set()
    max_marks = 200 if len(tokens) > 3_000 else 500

    def is_known(word: str) -> bool:
        key = word.casefold()
        hit = known_cache.get(key)
        if hit is None:
            hit = dictionary.contains(word) or dictionary.in_wordlist(word)
            known_cache[key] = hit
        return hit

    for token in tokens:
        if len(corrections) >= max_marks:
            break
        if not any(ch in _CONFUSABLE_CHARS for ch in token.text):
            continue
        folded = token.text.casefold()
        if folded in checked:
            continue
        checked.add(folded)
        if is_known(token.text):
            continue
        for variant in _variants(token.text, limit=16):
            # Hunspell accepts junk stems (бурт). Only trusted wordlist hits.
            if not dictionary.in_wordlist(variant):
                continue
            corrections.append(
                Correction(
                    id=str(uuid.uuid4()),
                    category=Category.SPELLING,
                    original_text=token.text,
                    suggested_text=variant,
                    explanation=(
                        "о/ө эсвэл у/ү төөрөлдсөн байж болзошгүй. Толь дахь үгээр солих санал."
                    ),
                    confidence=0.82,
                    start=token.start,
                    end=token.end,
                    source=Source.DICTIONARY,
                    rule_id="confusable_o_u",
                    severity=Severity.ERROR,
                )
            )
            break
    return corrections
