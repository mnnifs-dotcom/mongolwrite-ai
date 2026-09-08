from __future__ import annotations

from app.engine.dictionary import DictionaryProvider
from app.engine.misspellings import lookup_misspelling
from app.engine.models import Category, Correction

_REWRITE = frozenset(
    {
        Category.STYLE,
        Category.FORMALITY,
        Category.CLARITY,
        Category.WORD_CHOICE,
        Category.REDUNDANCY,
        Category.TERMINOLOGY,
        Category.AI_REWRITE,
    }
)


def filter_bad_suggestions(
    items: list[Correction],
    dictionary: DictionaryProvider,
) -> list[Correction]:
    return [item for item in items if _acceptable(item, dictionary)]


def _acceptable(item: Correction, dictionary: DictionaryProvider) -> bool:
    original = item.original_text.strip()
    suggested = item.suggested_text.strip()
    if not original or original == suggested:
        return False
    if not suggested:
        return item.category in _REWRITE
    if lookup_misspelling(suggested):
        return False
    compact = suggested.replace(" ", "").replace(",", "")
    space_only = compact.casefold() == original.casefold() and suggested != original
    if space_only and " " not in original and dictionary.contains(original):
        return False
    if item.category in _REWRITE:
        return True
    if " " not in original and " " in suggested and dictionary.contains(original):
        return False
    if dictionary.contains(original):
        return False
    return True
