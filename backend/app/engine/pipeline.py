from __future__ import annotations

import logging

from app.engine.confusables import check_confusables
from app.engine.dictionary import DictionaryProvider
from app.engine.homoglyphs import check_homoglyphs
from app.engine.models import Category, Correction
from app.engine.ranker import rank_corrections
from app.engine.repeats import check_repeated_words
from app.engine.spelling import check_spelling
from app.engine.text import to_nfc, tokenize

_log = logging.getLogger(__name__)

# Product surface: зөв бичих only (no word-choice / official-style noise).
_KEEP = {Category.SPELLING, Category.REDUNDANCY}


class LanguageEngine:
    def __init__(self, dictionary: DictionaryProvider | None = None) -> None:
        self.dictionary = dictionary or DictionaryProvider()

    def check(self, text: str, style: str = "government_official") -> list[Correction]:
        del style
        if not text.strip():
            return []
        _ = to_nfc(text)
        tokens = tokenize(text)
        raw: list[Correction] = []
        for checker in (
            lambda: check_repeated_words(tokens, text),
            lambda: check_homoglyphs(tokens, self.dictionary),
            lambda: check_confusables(tokens, self.dictionary),
            lambda: check_spelling(tokens, self.dictionary),
        ):
            try:
                raw.extend(checker())
            except Exception:
                _log.exception("checker failed")
        kept: list[Correction] = []
        for item in raw:
            if item.category not in _KEEP:
                continue
            # Present every mark as spelling in the editor.
            if item.category != Category.SPELLING:
                item = item.model_copy(update={"category": Category.SPELLING})
            kept.append(item)
        return rank_corrections(kept)
