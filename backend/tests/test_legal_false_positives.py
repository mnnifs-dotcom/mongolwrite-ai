"""Legalinfo statute text should not flood the editor with false positives."""

from __future__ import annotations

from pathlib import Path

from app.engine.dictionary import DictionaryProvider
from app.engine.legal_lexicon import load_legal_auto_lexicon
from app.engine.pipeline import LanguageEngine


def _law_sample() -> str:
    path = Path("/tmp/law12701_clean.txt")
    if path.is_file():
        return path.read_text(encoding="utf-8")[:40_000]
    return (
        "1.1.Энэ хуулийн зорилт нь шүүхийн шийдвэр гүйцэтгэх ажиллагааны үндэслэл, "
        "журмыг тогтоож, шүүхийн шийдвэр гүйцэтгэх байгууллагын тогтолцоо, "
        "алба хаагчийн эрх зүйн байдалтай холбогдон үүсэх харилцааг зохицуулахад оршино. "
        "Дараахь нөхцөлд эсхүл талаархи журмыг баримтална. Улаанбаатар хот."
    )


def test_legal_auto_lexicon_includes_statute_lemmas() -> None:
    words = load_legal_auto_lexicon()
    for lemma in ("эсхүл", "дараахь", "талаархи", "улаанбаатар", "батласан"):
        assert lemma in words


def test_law12701_sample_keeps_statute_spellings() -> None:
    text = _law_sample()
    engine = LanguageEngine(DictionaryProvider())
    corrections = engine.check(text)
    flagged = {item.original_text.casefold() for item in corrections}
    for lemma in ("эсхүл", "дараахь", "талаархи", "улаанбаатар"):
        if lemma in text.casefold():
            assert lemma not in flagged, f"{lemma} should not be flagged on statute text"
    # Pedantry rules on established forms should stay quiet.
    soft = [
        item
        for item in corrections
        if item.rule_id == "extra_soft_sign" and item.original_text.casefold() == "дараахь"
    ]
    assert not soft
