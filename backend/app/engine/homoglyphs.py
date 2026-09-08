from __future__ import annotations

import unicodedata
import uuid

from app.engine.dictionary import DictionaryProvider
from app.engine.misspellings import lookup_misspelling
from app.engine.models import Category, Correction, Severity, Source
from app.engine.text import Token, is_cyrillic_letter

# Latin letters commonly typed instead of Cyrillic lookalikes.
LATIN_TO_CYRILLIC = {
    "a": "а",
    "A": "А",
    "e": "е",
    "E": "Е",
    "o": "о",
    "O": "О",
    "p": "р",
    "P": "Р",
    "c": "с",
    "C": "С",
    "x": "х",
    "X": "Х",
    "y": "у",
    "Y": "У",
    "k": "к",
    "K": "К",
    "m": "м",
    "M": "М",
    "t": "т",
    "T": "Т",
    "h": "н",
    "H": "Н",
    "b": "в",
    "B": "В",
}


def _to_cyrillic(word: str) -> str | None:
    chars: list[str] = []
    changed = False
    for ch in word:
        if ch in LATIN_TO_CYRILLIC:
            chars.append(LATIN_TO_CYRILLIC[ch])
            changed = True
        elif is_cyrillic_letter(ch) or ch in "-'’":
            chars.append(ch)
        else:
            return None
    if not changed:
        return None
    return "".join(chars)


def _best_cyrillic(word: str, dictionary: DictionaryProvider | None) -> str | None:
    cyrillic = _to_cyrillic(word)
    if not cyrillic:
        return None
    if dictionary is None:
        return cyrillic
    fixed = lookup_misspelling(cyrillic)
    if fixed:
        return fixed
    if dictionary.contains(cyrillic) or dictionary.in_wordlist(cyrillic):
        return cyrillic
    hit = dictionary.suggest(cyrillic)
    if hit:
        return hit[0]
    return cyrillic


def check_homoglyphs(
    tokens: list[Token],
    dictionary: DictionaryProvider | None = None,
) -> list[Correction]:
    corrections: list[Correction] = []
    for token in tokens:
        has_latin = any("LATIN" in unicodedata.name(ch, "") for ch in token.text if ch.isalpha())
        has_cyrillic = any(is_cyrillic_letter(ch) for ch in token.text)
        if not has_latin:
            continue
        if not has_cyrillic and not all(
            (not ch.isalpha()) or ch in LATIN_TO_CYRILLIC for ch in token.text
        ):
            # Real English (has i, w, f, …) — leave it.
            continue
        suggested = _best_cyrillic(token.text, dictionary)
        if not suggested or suggested == token.text:
            continue
        mixed = has_latin and has_cyrillic
        corrections.append(
            Correction(
                id=str(uuid.uuid4()),
                category=Category.SPELLING,
                original_text=token.text,
                suggested_text=suggested,
                explanation=(
                    "Латин болон кирилл үсэг холилдсон байна."
                    if mixed
                    else "Англи гарын латин үсэг кирилл үгэнд орсон байна."
                ),
                confidence=0.9 if mixed else 0.75,
                start=token.start,
                end=token.end,
                source=Source.RULE,
                rule_id="homoglyph_latin_cyrillic",
                severity=Severity.ERROR if mixed else Severity.WARNING,
            )
        )
    return corrections
