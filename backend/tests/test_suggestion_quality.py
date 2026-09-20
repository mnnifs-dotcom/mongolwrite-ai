"""Regression: do not offer nonsense splits / neighbors for real Mongolian forms."""

from __future__ import annotations

from app.engine.runtime import get_engine, run_engine_check


def _marks(text: str) -> list:
    get_engine()
    return run_engine_check(text, "government_official")


def _for_word(text: str, word: str):
    return [c for c in _marks(text) if c.original_text.casefold() == word.casefold()]


def test_sadangiin_not_split_into_giin() -> None:
    hits = _for_word("төрөл садангийн бусад", "садангийн")
    assert hits == [], [f"{c.suggested_text}/{c.rule_id}" for c in hits]


def test_tolborteigeer_not_split_into_geer() -> None:
    hits = _for_word("төлбөртэйгээр захиран", "төлбөртэйгээр")
    assert hits == [], [f"{c.suggested_text}/{c.rule_id}" for c in hits]


def test_morini_suggests_dictionary_form_not_junk() -> None:
    hits = _for_word("мөрийний шинжийг агуулсан", "мөрийний")
    assert hits, "мөрийний should still be flagged"
    assert hits[0].suggested_text.casefold() == "мөрний"
    assert "мөрийийн" not in {
        hits[0].suggested_text.casefold(),
        *[s.casefold() for s in (hits[0].suggestions or [])],
    }


def test_khusch_suggests_khusezh_not_khuch() -> None:
    hits = _for_word("хүсч өргөдөл гаргасан байв", "хүсч")
    assert hits, "хүсч should be flagged"
    assert hits[0].suggested_text.casefold() == "хүсэж"
    assert hits[0].rule_id == "sej_converb"
    bad = {"хүч", "хүрч", *(s.casefold() for s in (hits[0].suggestions or []))}
    assert "хүч" not in {hits[0].suggested_text.casefold(), *(s.casefold() for s in (hits[0].suggestions or []))}


def test_real_glued_words_still_flagged() -> None:
    hits = _for_word("яагаадгэвэл тийм", "яагаадгэвэл")
    assert hits
    assert hits[0].suggested_text == "яагаад гэвэл"
