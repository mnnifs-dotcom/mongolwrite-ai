"""Systemic spelling: do not invent errors for Hunspell forms missed by seal."""

from __future__ import annotations

from app.engine.dictionary import DictionaryProvider
from app.engine.models import Category
from app.engine.pipeline import LanguageEngine

# Hunspell-known legal/formal forms that previously false-positive under seal.
_SEAL_SAMPLE = (
    "цочрол",
    "ойлгогдох",
    "задруулахгүй",
    "хаягласан",
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
)


def test_hunspell_forms_not_flagged_when_sealed_unprobed() -> None:
    dictionary = DictionaryProvider()
    assert dictionary.has_hunspell
    for lemma in _SEAL_SAMPLE:
        assert dictionary.hunspell_knows(lemma), lemma
    # Fresh seal without warming — simulates warm-budget miss on long docs.
    dictionary = DictionaryProvider()
    dictionary.seal_lookups()
    engine = LanguageEngine(dictionary)
    text = (
        "Хоригдлын сэтгэл зүйд цочрол үзүүлэх нууц тэмдэг үл ойлгогдох "
        "хэл дохиогоор задруулахгүй байх үүрэгтэй албан тушаалтанд хаягласан "
        "захидал. " + " ".join(_SEAL_SAMPLE)
    )
    flagged = {
        item.original_text.casefold()
        for item in engine.check(text)
        if item.category == Category.SPELLING
    }
    for lemma in _SEAL_SAMPLE:
        assert lemma not in flagged, f"{lemma} falsely flagged under sealed lookups"


def test_real_typos_still_flagged_when_probed() -> None:
    """Fail-open must not hide clear misspellings after Hunspell says no."""
    dictionary = DictionaryProvider()
    engine = LanguageEngine(dictionary)
    text = "Би одөр ажиллана танилццана"
    flagged = {
        item.original_text.casefold()
        for item in engine.check(text)
        if item.category == Category.SPELLING
    }
    assert "одөр" in flagged or "танилццана" in flagged
