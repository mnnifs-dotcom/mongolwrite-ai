from app.engine.dictionary import DictionaryProvider
from app.engine.pipeline import LanguageEngine

engine = LanguageEngine(DictionaryProvider(use_hunspell=False))

USER_SENTENCE = (
    "Манай байгууллагаас ирүүлсэн хүсэлтийг хүлээн авч, танилцан "
    "холбогдох арга хэмжээ авч ажиллана уу."
)
IMPROVED_SENTENCE = (
    "Манай байгууллагаас хүргүүлсэн хүсэлтийг хүлээн авч, танилцан, "
    "холбогдох арга хэмжээ авч ажиллана уу."
)


def by_rule(text: str, rule_id: str) -> list[str]:
    return [item.suggested_text for item in engine.check(text) if item.rule_id == rule_id]


def test_ours_irulelsen_becomes_hurgulsen() -> None:
    assert "хүргүүлсэн" in by_rule(USER_SENTENCE, "outgoing_delivery_verb")


def test_theirs_irulelsen_stays() -> None:
    text = "Танай байгууллагаас ирүүлсэн хүсэлтийг хүлээн авч ажиллана."
    assert by_rule(text, "outgoing_delivery_verb") == []
    assert by_rule(text, "incoming_delivery_verb") == []


def test_theirs_hurgulsen_becomes_irulelsen() -> None:
    text = "Танай байгууллагаас хүргүүлсэн хүсэлтийг хүлээн авсан."
    assert "ирүүлсэн" in by_rule(text, "incoming_delivery_verb")


def test_neutral_irulelsen_not_flagged() -> None:
    assert by_rule("Шинжилгээний хариу ирүүлсэн болно.", "outgoing_delivery_verb") == []


def test_reply_request_not_flagged() -> None:
    text = "Манай байгууллага хүсэлтийг хүлээн авч, хариу ирүүлнэ үү."
    assert by_rule(text, "outgoing_delivery_verb") == []


def test_we_will_send_reply() -> None:
    assert "хүргүүлнэ" in by_rule("бид ирүүлнэ", "outgoing_delivery_verb")


def test_comma_not_required_after_taniltsan() -> None:
    assert by_rule(USER_SENTENCE, "missing_comma_after_converb") == []


def test_improved_sentence_has_no_errors() -> None:
    errors = [item for item in engine.check(IMPROVED_SENTENCE) if item.severity == "error"]
    assert errors == []


def test_receive_document_official() -> None:
    found = engine.check("Хүсэлтийг авч шалгана.")
    assert any(item.suggested_text == "хүлээн авч" for item in found)


def test_send_yavuul_official() -> None:
    found = engine.check("Тайлан явуулсан болно.")
    assert any(item.suggested_text == "илгээсэн" for item in found)


def test_review_document_official() -> None:
    found = engine.check("Өргөдлийг үзэж шийдвэрлэнэ.")
    assert any(item.suggested_text == "танилцаж" for item in found)


def test_informal_yum() -> None:
    found = engine.check("Хүсэлт ирсэн юм.")
    assert any(item.rule_id == "informal_yum" for item in found)


def test_official_baina() -> None:
    found = engine.check("Хүсэлт ирүүлсэн байгаа.")
    assert any(item.suggested_text == "байна" for item in found)


def test_style_yaaj() -> None:
    found = engine.check("Энэ ажлыг яаж хийх вэ.")
    assert any(
        item.suggested_text == "хэрхэн" and item.rule_id == "official_kherkhen" for item in found
    )


def test_style_heregtei() -> None:
    found = engine.check("Тайланг хийх хэрэгтэй.")
    assert any(item.suggested_text == "хийх шаардлагатай" for item in found)


def test_style_think_and_then() -> None:
    found = engine.check("Бид тэгээд гэж бодож байна.")
    assert any(item.suggested_text == "улмаар" for item in found)
    assert any(item.suggested_text == "гэж үзэж" for item in found)


def test_style_redundancy() -> None:
    found = engine.check("Ажлыг дахин шинээр эхэлнэ.")
    assert any(item.suggested_text == "дахин" and item.rule_id == "redundant_again" for item in found)


def test_style_tiim_bolohor() -> None:
    found = engine.check("Тийм болохоор хариу хүргүүлнэ.")
    assert any(item.suggested_text == "Иймд" for item in found)


def test_style_keeps_official_sentence() -> None:
    text = "Хүсэлтийг хэрхэн шийдвэрлэхийг тодорхойлж, хариу хүргүүлнэ."
    ids = {item.rule_id for item in engine.check(text)}
    assert "official_kherkhen" not in ids
    assert "spoken_tiim_bolohor" not in ids
