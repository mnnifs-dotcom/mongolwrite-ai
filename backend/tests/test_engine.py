from __future__ import annotations

import pytest
from app.engine.dictionary import DictionaryProvider
from app.engine.pipeline import LanguageEngine

engine = LanguageEngine(DictionaryProvider(use_hunspell=False))


def rule_ids(text: str) -> set[str]:
    return {item.rule_id for item in engine.check(text)}


def has_rule(text: str, rule_id: str) -> bool:
    return rule_id in rule_ids(text)


def test_empty() -> None:
    assert engine.check("") == []


def test_unknown_without_suggestion_is_not_flagged() -> None:
    # Real-looking leftover without Hunspell stays quiet so missing lexicon
    # words are not mass-flagged. Gibberish is handled separately.
    assert engine.check("хыбх") == []


def test_gibberish_is_flagged_even_without_suggestion() -> None:
    text = "йыб йыбөроыбрэ ыробхө ро ыробхө ор"
    found = engine.check(text)
    originals = {item.original_text for item in found}
    assert "йыб" in originals
    assert "йыбөроыбрэ" in originals
    assert "ыробхө" in originals
    assert "ор" not in originals
    assert "ро" not in originals
    assert all(item.rule_id == "unknown_word" for item in found if item.original_text in originals)


def test_known_word_is_not_unknown() -> None:
    assert "unknown_word" not in rule_ids("өдөр")
    assert engine.check("боломжтой") == []
    assert engine.check("төөн") == []


def test_mongolian_letters_not_folded() -> None:
    text = "Өнөөдөр үүрэг хүлээн авсан."
    originals = {item.original_text for item in engine.check(text)}
    assert "Өнөөдөр" not in originals
    assert "үүрэг" not in originals


def test_burt_is_not_suggested_for_burt_front() -> None:
    found = engine.check("тухай бүрт нь эзэмших шаардлагатай")
    assert not any(item.original_text.casefold() == "бүрт" for item in found)


def test_known_words_not_confusable() -> None:
    for word in ("өдөр", "үг", "хүсэлт", "өргөдөл", "мөнгө"):
        assert "confusable_o_u" not in rule_ids(word)


def test_missing_vowel_in_ersdel() -> None:
    found = engine.check("эрсдлээс")
    assert any(item.suggested_text == "эрсдэлээс" for item in found)
    local = LanguageEngine(DictionaryProvider(frozenset({"эрсдэлээс", "эрсдэл"})))
    found = local.check("эрсдлээс")
    assert any(item.suggested_text == "эрсдэлээс" for item in found)


def test_user_sentence_spelling_and_comma() -> None:
    text = "Хүлээн авч танилццана уу."
    ids = rule_ids(text)
    assert "doubled_letter" in ids or "nearby_spelling" in ids
    assert "missing_comma_after_converb" not in ids
    found = engine.check(text)
    assert any(item.suggested_text.casefold() == "танилцана" for item in found)


def test_correct_official_sentence_no_spelling() -> None:
    text = "Хүлээн авч, танилцана уу."
    ids = rule_ids(text)
    assert "doubled_letter" not in ids
    assert "missing_comma_after_converb" not in ids


def test_avch_ajillana_does_not_need_comma() -> None:
    assert "missing_comma_after_converb" not in rule_ids("арга хэмжээ авч ажиллана")


def test_official_converb() -> None:
    found = engine.check("танилцаад")
    assert any(item.suggested_text == "танилцан" for item in found)
    found = engine.check("аваад")
    assert any(item.suggested_text == "авч" for item in found)


def test_official_style_skipped_in_standard() -> None:
    assert any(item.rule_id == "official_converb" for item in engine.check("танилцаад"))
    assert not any(
        item.rule_id == "official_converb"
        for item in engine.check("танилцаад", style="standard")
    )


def test_example_official_sentence() -> None:
    text = (
        "Манай байгууллагаас ирүүлсэн хүсэлтийг хүлээн авч танилцаад "
        "холбогдох арга хэмжээ авч ажиллана уу."
    )
    assert "official_converb" in rule_ids(text)


def test_number_thousands_comma_not_flagged() -> None:
    assert "missing_space_after_comma" not in rule_ids("1,000 төгрөг")


def test_custom_dictionary_repeat() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"фоо"})))
    assert local.check("фоо") == []
    assert any(item.rule_id == "repeated_word" for item in local.check("фоо фоо"))


PUNCT_CASES = [
    ("ажил  байна", "extra_whitespace"),
    ("тайлан  ирүүлсэн", "extra_whitespace"),
    ("үг ,", "space_before_punct"),
    ("үг .", "space_before_punct"),
    ("үг !", "space_before_punct"),
    ("үг ?", "space_before_punct"),
    ("үг ;", "space_before_punct"),
    ("үг :", "space_before_punct"),
    ("ажил ,", "space_before_punct"),
    ("үг,үг", "missing_space_after_comma"),
    ("ажил,байгууллага", "missing_space_after_comma"),
    ("тайлан,өргөдөл", "missing_space_after_comma"),
    ("тушаал,тогтоол", "missing_space_after_comma"),
    ("Зөвшөөрөх??", "repeated_punctuation"),
    ("Анхаар!!!", "repeated_punctuation"),
    ("Яаралтай!!", "repeated_punctuation"),
    ("дуусав....", "repeated_dots"),
    ("төгсөв.....", "repeated_dots"),
    ("Хүлээн авч танилцан холбогдох", "missing_comma_after_converb"),
]

REPEAT_CASES = [
    "хүсэлт хүсэлт",
    "байгууллага байгууллага",
    "ажил ажил",
    "Өдөр өдөр",
    "үг үг",
    "тушаал тушаал",
    "тайлан тайлан",
    "өргөдөл өргөдөл",
    "хариу хариу",
    "албан албан",
    "тогтоол тогтоол",
    "зөвлөмж зөвлөмж",
]

HOMO_CASES = [
    "хүсэлтp",
    "байгууллагаc",
    "ажилaн",
    "төрийнe",
    "уулзалтo",
    "тайланx",
    "өргөдөлy",
    "тушаалk",
    "мөнгөp",
    "хариуc",
    "өгүүлбэрa",
    "хуралo",
]

CONFUSABLE_CASES = [
    ("одөр", "өдөр"),
    ("уг", "үг"),
    ("оргодөл", "өргөдөл"),
    ("монго", "мөнгө"),
    ("хусэлт", "хүсэлт"),
    ("уйл", "үйл"),
    ("Одор", "Өдөр"),
]

CLEAN_CASES = [
    "Өнөөдөр үүрэг хүлээн авсан.",
    "Манай байгууллага хүсэлт хүлээн авч ажиллана.",
    "2026 оны 8 дугаар сарын 29-ний өдөр",
    "Шинжилгээний хариу ирүүлсэн болно.",
    "Албан бичиг, тайлан, тушаал.",
    "Нэр: Бат-Эрдэнэ",
    "Тоо: 12345",
    "өдөр үг өргөдөл хүсэлт мөнгө",
    "Хүндэтгэсэн.",
    "Албан тушаалтан ажиллана.",
    "Тушаал гарсан болно.",
]


@pytest.mark.parametrize("text,rule", PUNCT_CASES)
def test_punctuation_is_not_checked(text: str, rule: str) -> None:
    assert not has_rule(text, rule)


@pytest.mark.parametrize("text", REPEAT_CASES)
def test_repeat_bulk(text: str) -> None:
    assert has_rule(text, "repeated_word")


@pytest.mark.parametrize("text", HOMO_CASES)
def test_homoglyph_bulk(text: str) -> None:
    assert has_rule(text, "homoglyph_latin_cyrillic")


@pytest.mark.parametrize("text,expected", CONFUSABLE_CASES)
def test_confusable_bulk(text: str, expected: str) -> None:
    found = engine.check(text)
    assert any(item.suggested_text.casefold() == expected.casefold() for item in found)


@pytest.mark.parametrize("text", CLEAN_CASES)
def test_clean_text_has_no_errors(text: str) -> None:
    errors = [
        item
        for item in engine.check(text)
        if item.severity == "error" and item.rule_id != "unknown_word"
    ]
    assert errors == []


def test_correct_converb_is_not_a_punctuation_error() -> None:
    text = "танилцан холбогдох арга хэмжээ авч үзэж шалгана."
    originals = {item.original_text.casefold() for item in engine.check(text)}
    assert "танилцан" not in originals
    assert "үзэж" not in originals
    assert "missing_comma_after_converb" not in rule_ids(text)

