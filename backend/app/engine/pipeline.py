from __future__ import annotations

import logging

from app.engine.confusables import check_confusables
from app.engine.dictionary import DictionaryProvider
from app.engine.grammar import check_grammar
from app.engine.homoglyphs import check_homoglyphs
from app.engine.models import Correction
from app.engine.ranker import rank_corrections
from app.engine.repeats import check_repeated_words
from app.engine.spelling import check_spelling
from app.engine.style import check_official_style
from app.engine.text import to_nfc, tokenize
from app.engine.wordchoice import check_word_choice

_log = logging.getLogger(__name__)


class LanguageEngine:
    def __init__(self, dictionary: DictionaryProvider | None = None) -> None:
        self.dictionary = dictionary or DictionaryProvider()

    def check(self, text: str, style: str = "government_official") -> list[Correction]:
        if not text.strip():
            return []
        # Offsets stay on the original string. NFC is used only as a guard.
        _ = to_nfc(text)
        tokens = tokenize(text)
        raw: list[Correction] = []
        for checker in (
            lambda: check_repeated_words(tokens, text),
            lambda: check_homoglyphs(tokens, self.dictionary),
            lambda: check_confusables(tokens, self.dictionary),
            lambda: check_spelling(tokens, self.dictionary),
            lambda: check_grammar(tokens, text, self.dictionary),
            lambda: check_word_choice(tokens, text),
            lambda: check_official_style(tokens, text, style),
        ):
            try:
                raw.extend(checker())
            except Exception:
                _log.exception("checker failed")
        return rank_corrections(raw)
