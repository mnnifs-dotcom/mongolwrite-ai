from __future__ import annotations

from app.engine.models import Category
from app.engine.pipeline import LanguageEngine
from app.engine.text import is_cyrillic_letter, tokenize


def extract_accepted_candidates(engine: LanguageEngine, text: str) -> list[str]:
    """Cyrillic tokens that the checker did not flag as spelling errors."""
    flagged = {
        item.original_text.casefold()
        for item in engine.check(text)
        if item.category == Category.SPELLING
    }
    candidates: list[str] = []
    seen: set[str] = set()
    for token in tokenize(text):
        letters = [ch for ch in token.text if ch.isalpha()]
        if len(token.text) < 3 or not letters:
            continue
        if not all(is_cyrillic_letter(ch) for ch in letters):
            continue
        folded = token.text.casefold()
        if folded in flagged or folded in seen:
            continue
        seen.add(folded)
        candidates.append(token.text)
    return candidates


def learn_accepted_words(engine: LanguageEngine, text: str) -> list[str]:
    """Add Cyrillic words that were not flagged as spelling errors.

    Words already in the curated seed are skipped, so a long statute often
    yields only a handful of newly added forms — that is expected.
    """
    return engine.dictionary.add_words(extract_accepted_candidates(engine, text))
