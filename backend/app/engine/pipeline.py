from __future__ import annotations

import logging

from app.engine.confusables import check_confusables
from app.engine.dictionary import DictionaryProvider
from app.engine.grammar import _glued_forms
from app.engine.homoglyphs import check_homoglyphs
from app.engine.models import Category, Correction
from app.engine.ranker import rank_corrections
from app.engine.repeats import check_repeated_words
from app.engine.spelling import check_spelling
from app.engine.text import to_nfc, tokenize

_log = logging.getLogger(__name__)

# Product surface: зөв бичих only (no word-choice / official-style noise).
# Glued-word grammar hits are remapped to SPELLING below.
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
            # Missing spaces: ажиллажбайна → ажиллаж байна, байнауу → байна уу, …
            lambda: _glued_forms(tokens, self.dictionary),
            lambda: check_spelling(tokens, self.dictionary),
        ):
            try:
                raw.extend(checker())
            except Exception:
                _log.exception("checker failed")
        # Prefer glued-split marks over a later unknown_word on the same span.
        spanned = {(item.start, item.end) for item in raw if item.rule_id != "unknown_word"}
        kept: list[Correction] = []
        for item in raw:
            if item.category not in _KEEP and not (
                item.category == Category.GRAMMAR
                and item.rule_id
                and item.rule_id.startswith(("glued_", "separate_"))
            ):
                continue
            if item.rule_id == "unknown_word" and (item.start, item.end) in spanned:
                continue
            # Present every mark as spelling in the editor.
            if item.category != Category.SPELLING:
                item = item.model_copy(update={"category": Category.SPELLING})
            kept.append(item)
        return rank_corrections(kept)
