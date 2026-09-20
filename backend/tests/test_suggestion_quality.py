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
    assert "хүч" not in {
        hits[0].suggested_text.casefold(),
        *(s.casefold() for s in (hits[0].suggestions or [])),
    }


def test_sergesc_suggests_sergeezh_not_sergeen() -> None:
    hits = _for_word("сэргэсч ирэв", "сэргэсч")
    assert hits, "сэргэсч should be flagged"
    assert hits[0].suggested_text.casefold() == "сэргээж"
    assert hits[0].rule_id == "sej_converb"
    assert "сэргээн" not in {
        hits[0].suggested_text.casefold(),
        *(s.casefold() for s in (hits[0].suggestions or [])),
    }


def test_sch_junk_neighbors_not_offered() -> None:
    """Similar -сч typos must not get unrelated short dictionary neighbors."""
    for word, text, forbidden in (
        ("бисч", "бисч үлдэв", {"бич", "бийч"}),
        ("гасч", "гасч унтарлаа", {"гарч", "галч"}),
        ("тааласч", "тааласч байна", {"таалал", "таарч"}),
    ):
        hits = _for_word(text, word)
        offered = {
            *(h.suggested_text.casefold() for h in hits if h.suggested_text),
            *(s.casefold() for h in hits for s in (h.suggestions or [])),
        }
        assert not (offered & forbidden), f"{word}: {offered}"


def test_legitimate_sch_verbs_untouched() -> None:
    for word, text in (
        ("багасч", "багасч байна"),
        ("босч", "босч ирэв"),
        ("хасч", "хасч байна"),
        ("өсч", "өсч байна"),
    ):
        hits = _for_word(text, word)
        assert hits == [], f"{word}: {[f'{c.suggested_text}/{c.rule_id}' for c in hits]}"


def test_real_glued_words_still_flagged() -> None:
    hits = _for_word("яагаадгэвэл тийм", "яагаадгэвэл")
    assert hits
    assert hits[0].suggested_text == "яагаад гэвэл"
