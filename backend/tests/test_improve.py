from app.engine.dictionary import DictionaryProvider
from app.engine.improve import improve_text
from app.engine.pipeline import LanguageEngine

GARBLED = (
    "Манай байгууллагаас хүргүүлсэнэн хүсэлтийг хүлээн авчтанилцан,ан, "
    "холбогдох арга хэмжээ авч ажиллана уу."
)
CLEAN = (
    "Манай байгууллагаас хүргүүлсэн хүсэлтийг хүлээн авч, танилцан, "
    "холбогдох арга хэмжээ авч ажиллана уу."
)

engine = LanguageEngine(DictionaryProvider(use_hunspell=False))


def test_flags_glued_words() -> None:
    found = engine.check("хүлээн авчтанилцан холбогдох")
    assert any(
        item.rule_id == "glued_words" and "танилцан" in item.suggested_text for item in found
    )


def test_flags_extra_suffix() -> None:
    found = engine.check("хүргүүлсэнэн")
    assert any(item.suggested_text == "хүргүүлсэн" for item in found)


def test_flags_junk_comma_fragment() -> None:
    found = engine.check("танилцан,ан, холбогдох")
    assert not any(item.rule_id == "junk_comma_fragment" for item in found)


def test_improve_repairs_garbled_sentence() -> None:
    text, applied = improve_text(engine, GARBLED)
    assert applied > 0
    assert "хүргүүлсэнэн" not in text
    assert "авчтанилцан" not in text
    remaining = [
        item
        for item in engine.check(text)
        if item.severity == "error"
        and item.rule_id in {"glued_words", "extra_suffix"}
    ]
    assert remaining == []


def test_improve_sample_letter() -> None:
    original = (
        "Манай байгууллагаас ирүүлсэн хүсэлтийг хүлээн авч, танилцан "
        "холбогдох арга хэмжээ авч ажиллана уу."
    )
    text, _applied = improve_text(engine, original)
    assert "хүргүүлсэн" in text
    assert "танилцан" in text
    assert "ирүүлсэн" not in text
