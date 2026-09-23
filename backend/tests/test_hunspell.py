from pathlib import Path

import pytest
from app.engine.dictionary import DictionaryProvider, hunspell_base_path
from app.engine.pipeline import LanguageEngine

pytestmark = pytest.mark.skipif(
    not hunspell_base_path().with_suffix(".dic").exists(),
    reason="Run python scripts/fetch_mn_dictionary.py first",
)


def test_hunspell_accepts_common_word() -> None:
    provider = DictionaryProvider()
    assert provider.contains("өдөр")
    assert provider.contains("танилцана")


def test_letter_case_does_not_change_membership() -> None:
    """аав / ААВ / Аав are the same dictionary word (casefold)."""
    provider = DictionaryProvider()
    forms = ("аав", "ААВ", "Аав", "ААв")
    assert all(provider.contains(word) for word in forms)
    assert all(provider.in_seed(word) for word in forms)
    assert all(provider.hunspell_knows(word) for word in forms)

    engine = LanguageEngine()
    for word in forms:
        assert not any(
            item.original_text == word and item.category == "SPELLING" and item.rule_id != "repeated_word"
            for item in engine.check(word)
        ), word


def test_hunspell_files_present() -> None:
    base = hunspell_base_path()
    assert Path(f"{base}.dic").exists()
    assert Path(f"{base}.aff").exists()


def test_hunspell_suffix_harmony_ablative() -> None:
    found = LanguageEngine().check("өдрээс")
    assert any(item.suggested_text == "өдрөөс" for item in found)


def test_correct_common_words_are_not_flagged() -> None:
    engine = LanguageEngine()
    local = LanguageEngine(DictionaryProvider(use_hunspell=False))
    for word in ("боломжтой", "төөн"):
        assert not any(item.original_text == word for item in engine.check(word))
        assert not any(item.original_text == word for item in local.check(word))


def test_common_correct_words_are_not_flagged() -> None:
    text = "Зарим ажилтан хуралдаа хоцорч ирсэн учраас төлөвлөгөөг хэлэлцжээ."
    found = LanguageEngine().check(text)
    originals = {item.original_text.casefold() for item in found}
    for word in ("зарим", "хуралдаа", "хоцорч", "ирсэн", "учраас", "төлөвлөгөөг", "хэлэлцжээ"):
        assert word not in originals


def test_correct_shaardlagatai_is_not_flagged() -> None:
    found = LanguageEngine().check("ажлаа цаг тухайд нь цэгцлэх шаардлагатай юм.")
    assert not any(item.original_text == "шаардлагатай" for item in found)


def test_shaardagtai_suggests_common_word() -> None:
    found = LanguageEngine().check("шаардагтай")
    item = next(row for row in found if row.original_text == "шаардагтай")
    assert item.suggested_text == "шаардлагатай"


def test_missing_a_in_shaardlagatai() -> None:
    found = LanguageEngine().check("шаардлагтай")
    item = next(row for row in found if row.original_text == "шаардлагтай")
    assert item.suggested_text == "шаардлагатай"
    assert "шаардагтай" not in [item.suggested_text, *item.suggestions]


def test_keeps_accusative_on_shaardlagataig() -> None:
    found = LanguageEngine().check("шаардлагтайг")
    item = next(row for row in found if row.original_text == "шаардлагтайг")
    options = [item.suggested_text, *item.suggestions]
    assert item.suggested_text == "шаардлагатайг"
    assert "шаардлагатайг" in options


def test_missing_g_in_shaardlagatai() -> None:
    found = LanguageEngine().check("цагтаа ирж ажиллах шаардлатай")
    item = next(row for row in found if row.original_text == "шаардлатай")
    assert item.suggested_text == "шаардлагатай"


def test_prefers_word_already_in_document() -> None:
    found = LanguageEngine().check("шаардлагатай ажилчид шаардлатай")
    item = next(row for row in found if row.original_text == "шаардлатай")
    assert item.suggested_text == "шаардлагатай"


def test_prefers_common_meeting_word() -> None:
    found = LanguageEngine().check("хурлалдаа")
    item = next(row for row in found if row.original_text == "хурлалдаа")
    assert item.suggested_text == "хуралдаа"


def test_offers_several_nearby_words() -> None:
    dictionary = DictionaryProvider(
        frozenset({"амжилт", "амжилтын", "амжилтад", "амжилтанд", "ажилтанд", "амжилтаид", "амжилтнд"})
    )
    options = dictionary.suggest_many("амжилтаинд", limit=8)
    assert len(options) >= 3
    assert {"амжилтад", "амжилтын", "амжилтанд", "ажилтанд", "амжилтаид"} & set(options)


def test_nearby_list_prefers_real_words() -> None:
    found = LanguageEngine().check("амжилтанд")
    item = next(row for row in found if row.original_text == "амжилтанд")
    options = [item.suggested_text, *item.suggestions]
    assert item.suggested_text == "амжилтад"
    assert len(options) >= 3
    assert "амжилтадд" not in options
    assert "амжилтд" not in options
    assert {"амжилтад", "амжилтын", "амжилтынд", "ажилтанд"} & set(options)


def test_suggests_list_for_vowel_drop() -> None:
    found = LanguageEngine().check("эхэлээгүй авчираагүй")
    by_word = {item.original_text: item for item in found}
    assert by_word["эхэлээгүй"].suggested_text == "эхлээгүй"
    assert by_word["авчираагүй"].suggested_text == "авчраагүй"
    assert "эхлээгүй" in (
        [by_word["эхэлээгүй"].suggested_text] + by_word["эхэлээгүй"].suggestions
    )
    assert "авчраагүй" in (
        [by_word["авчираагүй"].suggested_text] + by_word["авчираагүй"].suggestions
    )


def test_hunspell_negative_gui() -> None:
    found = LanguageEngine().check("ойлгохгуй")
    assert any(item.suggested_text == "ойлгохгүй" for item in found)


def test_employees_plural_and_each_other() -> None:
    found = LanguageEngine().check("ажилтангууд бие биенээ хүндэтгэж")
    by_word = {item.original_text: item for item in found}
    assert "биенээ" not in by_word
    assert by_word["ажилтангууд"].suggested_text == "ажилтнууд"


def test_bichigee_suggests_i_drop() -> None:
    engine = LanguageEngine()
    found = engine.check("бичигээ мартсан байлаа")
    item = next(row for row in found if row.original_text == "бичигээ")
    assert item.suggested_text == "бичгээ"
    assert item.rule_id == "i_drop"
    assert not any(row.original_text == "бичгээ" for row in engine.check("бичгээ"))


def test_i_drop_on_other_known_stems() -> None:
    engine = LanguageEngine()
    cases = (
        ("элчигээ", "элчгээ"),
        ("элчигийн", "элчгийн"),
        ("бичигээр", "бичгээр"),
        ("орчиноо", "орчноо"),
        ("ажилаа", "ажлаа"),
    )
    for original, wanted in cases:
        found = engine.check(original)
        item = next(row for row in found if row.original_text == original)
        assert item.suggested_text == wanted, original


def test_n_plural_and_x_reflexive_forms() -> None:
    engine = LanguageEngine()
    cases = (
        ("мэргэжилтэнгүүдийн", "мэргэжилтнүүдийн"),
        ("мэргэжилтэнгүүд", "мэргэжилтнүүд"),
        ("оюутангууд", "оюутнууд"),
        ("дүнүүдийн", "дүнгүүдийн"),
        ("дүнүүд", "дүнгүүд"),
        ("бичихдаа", "бичихдээ"),
        ("явахдоо", "явахдаа"),
        ("боловсруулахдоо", "боловсруулахдаа"),
    )
    for original, wanted in cases:
        found = engine.check(original)
        item = next(row for row in found if row.original_text == original)
        assert item.suggested_text == wanted, original
    for word in (
        "мэргэжилтнүүдийн",
        "дүнгүүдийн",
        "боловсруулахдаа",
        "орчинг",
        "оронгууд",
        "явахдаа",
        "бичихдээ",
        "ойлгохдоо",
        "давтамжийг",
        "цагийг",
    ):
        assert not any(item.original_text == word for item in engine.check(word)), word


def test_vowel_before_verb_x() -> None:
    engine = LanguageEngine()
    cases = (
        ("байгуулхаар", "байгуулахаар"),
        ("байгуулхад", "байгуулахад"),
        ("сайжруулхаар", "сайжруулахаар"),
        ("явхаар", "явахаар"),
        ("бичхээр", "бичихээр"),
        ("үзхээр", "үзэхээр"),
        ("бодхоор", "бодохоор"),
        ("ойлгхоор", "ойлгохоор"),
        ("ажиллхаар", "ажиллахаар"),
        ("эхлхээр", "эхлэхээр"),
        ("туслхаар", "туслахаар"),
        ("байгуулхгүй", "байгуулахгүй"),
        ("боловсруулхдоо", "боловсруулахдаа"),
        ("байгуулхдаа", "байгуулахдаа"),
    )
    for original, wanted in cases:
        found = engine.check(original)
        item = next(row for row in found if row.original_text == original)
        assert item.suggested_text == wanted, original
    for word in ("байгуулахаар", "явахаар", "бичихээр", "байгуулахад", "хийхээр"):
        assert not any(item.original_text == word for item in engine.check(word)), word


def test_palatal_case_zh_sh_ch_g() -> None:
    engine = LanguageEngine()
    cases = (
        ("давтамжыг", "давтамжийг"),
        ("давтамжын", "давтамжийн"),
        ("цагыг", "цагийг"),
        ("багшыг", "багшийг"),
        ("жолоочыг", "жолоочийг"),
    )
    for original, wanted in cases:
        found = engine.check(original)
        item = next(row for row in found if row.original_text == original)
        assert item.suggested_text == wanted, original
    for word in ("давтамжийг", "цагийг", "багшийг", "жолоочийг", "ажлыг"):
        assert not any(item.original_text == word for item in engine.check(word)), word


def test_lah_verb_habitual_and_related_forms() -> None:
    engine = LanguageEngine()
    cases = (
        ("тусладаг", "тусалдаг"),
        ("эхлэдэг", "эхэлдэг"),
        ("дууладаг", "дуулдаг"),
        ("усладаг", "усалдаг"),
        ("огтлодог", "огтолдог"),
        ("батладаг", "баталдаг"),
        ("нууцладаг", "нууцалдаг"),
        ("боловсрууладаг", "боловсруулдаг"),
        ("тусласан", "тусалсан"),
        ("туслаж", "тусалж"),
        ("туслана", "тусална"),
        ("эхлэнэ", "эхэлнэ"),
    )
    for original, wanted in cases:
        found = engine.check(original)
        item = next(row for row in found if row.original_text == original)
        assert item.suggested_text == wanted, original
        assert wanted in [item.suggested_text, *item.suggestions]
    for word in (
        "хайрладаг",
        "ажилладаг",
        "цэвэрлэдэг",
        "төлөвлөдөг",
        "завсарладаг",
        "бөглөдөг",
        "тусалдаг",
        "эхэлдэг",
        "дуулдаг",
    ):
        assert not any(item.original_text == word for item in engine.check(word)), word


def test_lagatai_and_khed_forms_are_kept() -> None:
    engine = LanguageEngine()
    for word in ("санаачлагатай", "хариуцлагатай", "дээшлүүлэхэд", "сайжруулахад", "бичихэд"):
        found = [item for item in engine.check(word) if item.original_text == word]
        assert not found, word
        assert not any(item.suggested_text == "санаачлаатай" for item in engine.check("санаачлагатай"))
    engine = LanguageEngine()
    for word in (
        "усны",
        "гарын",
        "нэрийн",
        "номын",
        "усанд",
        "уснаас",
        "номноос",
        "номонд",
        "жилнээс",
        "биеийнхээ",
        "ээжийнхээ",
    ):
        assert not any(item.original_text == word for item in engine.check(word)), word


def test_does_not_suggest_broken_case_forms() -> None:
    engine = LanguageEngine()
    found = engine.check("гарчигийг")
    item = next(row for row in found if row.original_text == "гарчигийг")
    options = [item.suggested_text, *item.suggestions]
    assert item.suggested_text == "гарчгийг"
    assert "гарчгыг" not in options
    found = engine.check("баримтийн")
    item = next(row for row in found if row.original_text == "баримтийн")
    options = [item.suggested_text, *item.suggestions]
    assert item.suggested_text == "баримтын"
    assert "бармтын" not in options
    assert "бармтийн" not in options
    found = engine.check("судалгааний")
    item = next(row for row in found if row.original_text == "судалгааний")
    options = [item.suggested_text, *item.suggestions]
    assert item.suggested_text == "судалгааны"
    assert "судалгааын" not in options
    assert not any(item.original_text == "судалгааны" for item in engine.check("судалгааны"))
    assert not any(item.original_text == "баримтын" for item in engine.check("баримтын"))


def test_niy_genitive_on_several_stems() -> None:
    engine = LanguageEngine()
    cases = (
        ("биенийхээ", "биеийнхээ"),
        ("ээжнийхээ", "ээжийнхээ"),
        ("нэрнийхээ", "нэрийнхээ"),
        ("аавныхаа", "аавынхаа"),
        ("биений", "биеийн"),
        ("ээжний", "ээжийн"),
    )
    for original, wanted in cases:
        found = engine.check(original)
        item = next(row for row in found if row.original_text == original)
        options = [item.suggested_text, *item.suggestions]
        assert item.suggested_text == wanted, original
        assert not any(opt[1:] == original[1:] and opt[:1] != original[:1] for opt in options)


def test_known_forms_that_keep_i_are_not_forced() -> None:
    engine = LanguageEngine()
    for word in ("харилаа", "цахимаа", "биенээ"):
        assert not any(item.original_text == word for item in engine.check(word))


def test_latin_a_in_ajiltanguud() -> None:
    found = LanguageEngine().check("ажилт" + "a" + "нгууд")
    assert any(item.suggested_text == "ажилтнууд" for item in found)


def test_computer_loanword_not_unknown() -> None:
    found = LanguageEngine().check("компьютерийн компьютертээ")
    originals = {item.original_text.casefold() for item in found}
    assert "компьютерийн" not in originals
    assert "компьютертээ" not in originals


def test_correct_burt_not_flagged() -> None:
    found = LanguageEngine().check("тухай бүрт нь мэдэгдэнэ.")
    assert not any(item.original_text.casefold() == "бүрт" for item in found)
    assert not any(item.suggested_text.casefold() == "бурт" for item in found)


def test_gibberish_flagged_with_hunspell() -> None:
    found = LanguageEngine().check("йыб ыробхө")
    originals = {item.original_text for item in found}
    assert originals >= {"йыб", "ыробхө"}
    assert all(item.suggested_text == "" for item in found if item.rule_id == "unknown_word")


def test_frequency_suggests_missing_letter_in_common_word() -> None:
    engine = LanguageEngine()
    cases = (
        ("технолги", "технологи"),
        ("байгууллаг", "байгууллага"),
    )
    for original, wanted in cases:
        found = engine.check(original)
        item = next(row for row in found if row.original_text == original)
        assert item.suggested_text == wanted, original
        assert wanted in [item.suggested_text, *item.suggestions]


def test_random_typed_words_are_flagged() -> None:
    found = LanguageEngine().check("гыхбөшг шхшгхшхг нан")
    originals = {item.original_text for item in found}
    assert originals >= {"гыхбөшг", "шхшгхшхг", "нан"}


def test_established_loanwords_are_kept() -> None:
    engine = LanguageEngine()
    for word in ("вэбсайт", "вэбсайтад", "оффис", "оффисын"):
        assert not any(item.original_text == word for item in engine.check(word)), word
    assert not any(item.suggested_text == "вебсайт" for item in engine.check("вэбсайт"))
    assert not any(item.suggested_text == "офис" for item in engine.check("оффис"))


def test_sch_converb_suggests_school_vowel_zh() -> None:
    engine = LanguageEngine()
    expected = {
        "багасч": "багасаж",
        "босч": "босож",
        "хасч": "хасаж",
        "өсч": "өсөж",
    }
    for word, want in expected.items():
        found = engine.check(word)
        item = next(row for row in found if row.original_text == word)
        assert item.suggested_text == want, word
        assert item.rule_id == "sej_converb", word
    assert not any(item.suggested_text == "балгас" for item in engine.check("багасч"))


def test_misplaced_soft_sign_suggests_computer() -> None:
    engine = LanguageEngine()
    found = engine.check("комьпютер")
    item = next(row for row in found if row.original_text == "комьпютер")
    assert item.suggested_text == "компьютер"
    assert not any(item.original_text == "компьютер" for item in engine.check("компьютер"))


def test_extra_soft_sign_has_suggestion() -> None:
    engine = LanguageEngine()
    found = engine.check("дурьдагдаагүй")
    item = next(row for row in found if row.original_text == "дурьдагдаагүй")
    assert item.suggested_text == "дурдагдаагүй"
    assert not any(item.original_text == "дурдагдаагүй" for item in engine.check("дурдагдаагүй"))


def test_frequent_neighbors_fill_empty_suggestions() -> None:
    engine = LanguageEngine()
    cases = (
        ("судлага", "судалгаа"),
        ("байгуулгын", "байгууллагын"),
        ("технологий", "технологийн"),
        ("байгуулагла", "байгууллага"),
        ("байглуулга", "байгууллага"),
        ("байгуулглаа", "байгууллага"),
        ("мэдилээл", "мэдээлэл"),
        ("хөгжилл", "хөгжил"),
        ("интэрнэт", "интернет"),
        ("ажлиатан", "ажилтан"),
    )
    for original, wanted in cases:
        found = engine.check(original)
        item = next(row for row in found if row.original_text == original)
        assert item.suggested_text == wanted, (original, item.suggested_text)
        assert wanted not in ("", original)
