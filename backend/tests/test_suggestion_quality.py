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


def test_screenshot_sch_phrase() -> None:
    """Exact user phrase: хүсч, сэргээсч, баясч, хийсч, хэсч."""
    text = "хүсч → хүсэж, сэргээсч → сэргээж, баясч / хийсч / хэсч"
    expected = {
        "хүсч": "хүсэж",
        "сэргээсч": "сэргээж",
        "баясч": "баясаж",
        "хийсч": "хийсэж",
        "хэсч": "хэсэж",
    }
    for word, want in expected.items():
        hits = _for_word(text, word)
        assert hits, f"{word} should be flagged"
        assert hits[0].suggested_text.casefold() == want, word
        assert hits[0].rule_id == "sej_converb", word
        assert "сэргээн" not in {
            hits[0].suggested_text.casefold(),
            *(s.casefold() for s in (hits[0].suggestions or [])),
        }
    # Correct forms after the arrows must stay clean.
    for good in ("хүсэж", "сэргээж"):
        assert _for_word(text, good) == []


def test_sergesc_short_stem_also_sergeezh() -> None:
    hits = _for_word("сэргэсч ирэв", "сэргэсч")
    assert hits, "сэргэсч should be flagged"
    assert hits[0].suggested_text.casefold() == "сэргээж"
    assert hits[0].rule_id == "sej_converb"


def test_similar_sch_family_generalizes() -> None:
    """Not only screenshot words — same -сч family across stems."""
    cases = (
        ("бэлдэсч", "бэлдэж"),
        ("уншсч", "уншиж"),
        ("явсч", "явж"),
        ("бичсч", "бичиж"),
        ("ярьсч", "ярьж"),
        ("хайсч", "хайж"),
        ("идсч", "идэж"),
        ("авсч", "авч"),
        ("авасч", "авч"),
        ("загасч", "загасаж"),
        ("зогсч", "зогсож"),
        ("дуусч", "дуусаж"),
        ("төлсч", "төлж"),
        ("бүтэсч", "бүтээж"),
        ("бүтээсч", "бүтээж"),
        ("санасч", "санаж"),
        ("мэдэсч", "мэдэж"),
        ("болгосч", "болгож"),
        ("өгөсч", "өгч"),
        ("оросч", "орож"),
        ("явасч", "явж"),
        ("сэргэсч", "сэргээж"),
    )
    for word, want in cases:
        hits = _for_word(f"{word} байна", word)
        assert hits, f"{word} should be flagged"
        assert hits[0].suggested_text.casefold() == want, (word, hits[0].suggested_text)
        assert hits[0].rule_id == "sej_converb", word


def test_sch_no_false_short_stem_junk() -> None:
    """Do not map бүсч→бүж via noun бүх; leave without junk neighbors."""
    hits = _for_word("бүсч байна", "бүсч")
    offered = {
        *(h.suggested_text.casefold() for h in hits if h.suggested_text),
        *(s.casefold() for h in hits for s in (h.suggestions or [])),
    }
    assert "бүж" not in offered
    assert "бүсэж" not in offered
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


def test_sch_school_converbs_suggest_vowel_zh() -> None:
    """багасч/босч/хасч/өсч → багасаж/босож/хасаж/өсөж (never leave -сч)."""
    cases = (
        ("багасч", "багасч, босч", "багасаж"),
        ("босч", "багасч, босч, хасч, өсч", "босож"),
        ("хасч", "хасч байна", "хасаж"),
        ("өсч", "өсч байна", "өсөж"),
    )
    for word, text, want in cases:
        hits = _for_word(text, word)
        assert hits, f"{word} should be flagged"
        assert hits[0].suggested_text.casefold() == want, word
        assert hits[0].rule_id == "sej_converb", word
        assert hits[0].suggested_text.casefold().endswith("ж")
        assert not hits[0].suggested_text.casefold().endswith("сч")


def test_real_glued_words_still_flagged() -> None:
    hits = _for_word("яагаадгэвэл тийм", "яагаадгэвэл")
    assert hits
    assert hits[0].suggested_text == "яагаад гэвэл"
