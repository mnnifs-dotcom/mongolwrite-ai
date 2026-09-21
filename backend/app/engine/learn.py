from __future__ import annotations

from app.engine.hunspell_candidates import in_curated_lexicon, queue_review_words
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


def learn_accepted_words(
    engine: LanguageEngine,
    text: str,
    *,
    reason: str = "Шалгагч зөвшөөрсөн · шалгах багцад",
    tier: str = "reliable",
) -> list[str]:
    """Queue checker-accepted Cyrillic words for admin review (no lexicon write).

    Words already in the curated seed are skipped. Lexicon membership only
    happens after an admin keeps/approves them in «Шалгах багц».
    """
    candidates = extract_accepted_candidates(engine, text)
    to_queue = [
        word for word in candidates if not in_curated_lexicon(engine.dictionary, word)
    ]
    result = queue_review_words(
        to_queue,
        reason=reason,
        tier=tier,
        dictionary=engine.dictionary,
        skip_curated=True,
    )
    return list(result.get("queued") or [])
