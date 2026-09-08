from app.ai.locate import locate_corrections
from app.ai.provider import _parse_json
from app.ai.validate import filter_bad_suggestions
from app.engine.dictionary import DictionaryProvider
from app.engine.models import Category, Correction, Severity, Source
from app.engine.pipeline import LanguageEngine


def test_locate_unknown_word() -> None:
    found = locate_corrections(
        "хыбх өдөр",
        [
            {
                "original": "хыбх",
                "suggested": "хэв",
                "category": "SPELLING",
                "explanation": "Тольд байхгүй.",
                "severity": "error",
            }
        ],
    )
    assert len(found) == 1
    assert found[0].start == 0
    assert found[0].end == 4
    assert found[0].suggested_text == "хэв"
    assert found[0].source == "AI"


def test_locate_skips_missing_span() -> None:
    assert locate_corrections("өдөр", [{"original": "одөр", "suggested": "өдөр"}]) == []


def test_locate_uses_second_occurrence() -> None:
    found = locate_corrections(
        "ажил ажил",
        [
            {"original": "ажил", "suggested": "ажиллагаа"},
            {"original": "ажил", "suggested": "ажилт"},
        ],
    )
    assert [item.start for item in found] == [0, 5]


def test_parse_fenced_json() -> None:
    data = _parse_json('```json\n{"corrections":[]}\n```')
    assert data == {"corrections": []}


def _ai_item(original: str, suggested: str) -> Correction:
    return Correction(
        id="1",
        category=Category.GRAMMAR,
        original_text=original,
        suggested_text=suggested,
        explanation="тест",
        confidence=0.8,
        start=0,
        end=len(original),
        source=Source.AI,
        rule_id="ai_grammar",
        severity=Severity.ERROR,
    )


def test_rejects_breaking_common_word() -> None:
    dictionary = DictionaryProvider()
    kept = filter_bad_suggestions(
        [_ai_item("шаардлагатай", "шаардагтай")],
        dictionary,
    )
    assert kept == []


def test_rejects_split_of_known_word() -> None:
    dictionary = DictionaryProvider()
    kept = filter_bad_suggestions(
        [
            _ai_item("хуралдаа", "хур лалдаа"),
            _ai_item("шаардлагатай", "шаард лагтай"),
            _ai_item("одөр", "өдөр"),
        ],
        dictionary,
    )
    assert [item.original_text for item in kept] == ["одөр"]


def test_keeps_real_word_fix() -> None:
    dictionary = DictionaryProvider()
    kept = filter_bad_suggestions([_ai_item("эхэлээгүй", "эхлээгүй")], dictionary)
    assert kept[0].suggested_text == "эхлээгүй"


def test_keeps_style_rewrite_of_known_word() -> None:
    dictionary = DictionaryProvider()
    item = Correction(
        id="2",
        category=Category.STYLE,
        original_text="яаж",
        suggested_text="хэрхэн",
        explanation="найруулга",
        confidence=0.66,
        start=0,
        end=4,
        source=Source.AI,
        rule_id="ai_style",
        severity=Severity.SUGGESTION,
    )
    kept = filter_bad_suggestions([item], dictionary)
    assert kept[0].suggested_text == "хэрхэн"


def test_known_words_not_split_by_engine() -> None:
    found = LanguageEngine().check("хуралдаа шаардлагатай")
    assert found == []
