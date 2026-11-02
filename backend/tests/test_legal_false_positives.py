"""Legalinfo statute text should not flood the editor with false positives."""

from __future__ import annotations

from pathlib import Path

from app.engine.dictionary import DictionaryProvider
from app.engine.legal_lexicon import load_legal_auto_lexicon
from app.engine.models import Category
from app.engine.pipeline import LanguageEngine
from app.engine.spelling import _apply_case

_FP_BATCH = (
    "сэжигтнийг",
    "боловсролоор",
    "зуруулж",
    "факс",
    "гүйцэтгэвэл",
    "хэтэрснээс",
    "регистрийн",
    "биелүүлбэл",
    "учруулахааргүй",
    "барагдуулахаар",
    "нөлөөлөхөөргүй",
    "эвлэрч",
    "нуугдмал",
    "ирүүлэхгүй",
    "чадамж",
    "ялгаварлахгүйгээр",
)


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
    for lemma in _FP_BATCH:
        assert lemma in words, f"{lemma} should be in legal auto lexicon"


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


def test_editor_fp_batch_survives_sealed_lookups() -> None:
    """Hunspell-only forms must stay correct even when lookups are sealed."""
    dictionary = DictionaryProvider()
    for lemma in _FP_BATCH:
        assert dictionary.in_seed(lemma), lemma
    dictionary.seal_lookups()
    engine = LanguageEngine(dictionary)
    text = (
        "Үндэсний аюулгүй байдлын сэжигтнийг баривчлах боловсролоор "
        "ялгаварлахгүйгээр зуруулж гардуулсан факс гүйцэтгэвэл зохих "
        "хэтэрснээс хойш регистрийн дугаар биелүүлбэл учруулахааргүй "
        "барагдуулахаар нөлөөлөхөөргүй эвлэрч нуугдмал ирүүлэхгүй чадамж."
    )
    flagged = {
        item.original_text.casefold()
        for item in engine.check(text)
        if item.category == Category.SPELLING
    }
    for lemma in ("үндэсний", *_FP_BATCH):
        assert lemma not in flagged, f"{lemma} falsely flagged under sealed lookups"


def test_apply_case_offers_lowercase_suggestions() -> None:
    """Users should see dictionary-style lowercase suggestions (аав, not ААВ)."""
    assert _apply_case("ҮНДЭСНИЙ", "үндэсний") == "үндэсний"
    assert _apply_case("Үндэсний", "үндэсний") == "үндэсний"
    assert _apply_case("үндэсний", "үндэсний") == "үндэсний"
    assert _apply_case("ААВВ", "аав") == "аав"
    assert _apply_case("ӨДРЭЭС", "өдрөөс") == "өдрөөс"
