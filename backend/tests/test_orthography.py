from app.engine.dictionary import DictionaryProvider
from app.engine.pipeline import LanguageEngine

engine = LanguageEngine(DictionaryProvider(use_hunspell=False))


def rule_ids(text: str) -> set[str]:
    return {item.rule_id for item in engine.check(text)}


def suggestion(text: str, rule_id: str) -> str | None:
    for item in engine.check(text):
        if item.rule_id == rule_id:
            return item.suggested_text
    return None


def test_question_particle_back_vowel() -> None:
    assert suggestion("байна үү", "question_particle_harmony") == "уу"
    assert "question_particle_harmony" not in rule_ids("байна уу")


def test_question_particle_front_vowel() -> None:
    assert suggestion("ирнэ уу", "question_particle_harmony") == "үү"
    assert "question_particle_harmony" not in rule_ids("ирнэ үү")


def test_official_sentence_keeps_uu() -> None:
    assert "question_particle_harmony" not in rule_ids("Хүлээн авч, танилцана уу.")


def test_ve_particle() -> None:
    assert suggestion("хэн вэ", "ve_particle_harmony") == "бэ"
    assert suggestion("юу бэ", "ve_particle_harmony") == "вэ"
    assert "ve_particle_harmony" not in rule_ids("хэн бэ")
    assert "ve_particle_harmony" not in rule_ids("юу вэ")


def test_directive_particle() -> None:
    assert suggestion("өдөр руу", "directive_harmony") == "рүү"
    assert suggestion("ном рүү", "directive_harmony") == "руу"
    assert "directive_harmony" not in rule_ids("өдөр рүү")
    assert "directive_harmony" not in rule_ids("ном руу")


def test_glued_question_particle() -> None:
    assert suggestion("байнауу", "glued_question_particle") == "байна уу"
    assert suggestion("ирнэүү", "glued_question_particle") == "ирнэ үү"


def test_glued_auxiliary() -> None:
    assert suggestion("үзэжбайна", "glued_auxiliary") == "үзэж байна"
    assert suggestion("ажиллажбайна", "glued_auxiliary") == "ажиллаж байна"
    assert suggestion("авчбайна", "glued_auxiliary") == "авч байна"


def test_common_misspellings() -> None:
    assert suggestion("ягаад", "common_misspelling") == "яагаад"
    assert suggestion("гэхмэт", "common_misspelling") == "гэх мэт"
    assert suggestion("байхгуй", "common_misspelling") == "байхгүй"
    assert suggestion("гуйцэтгэх", "common_misspelling") == "гүйцэтгэх"
    # «ямарч» is also caught as a glued particle; either rule is fine.
    assert suggestion("ямарч", "separate_particle") == "ямар ч" or suggestion(
        "ямарч", "common_misspelling"
    ) == "ямар ч"
    assert suggestion("шаардлагтай", "common_misspelling") == "шаардлагатай"
    assert suggestion("шаардагтай", "common_misspelling") == "шаардлагатай"
    assert suggestion("шаардлагтайг", "common_misspelling") == "шаардлагатайг"


def test_suffix_harmony_ablative() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"өдрөөс", "өдөр"})))
    found = local.check("өдрээс")
    assert any(
        item.suggested_text == "өдрөөс" and item.rule_id == "suffix_harmony" for item in found
    )


def test_suffix_harmony_genitive() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"хүсэлтийн", "хүсэлт"})))
    found = local.check("хүсэлтын")
    assert any(item.suggested_text == "хүсэлтийн" for item in found)


def test_suffix_harmony_comitative() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"ээжтэй", "ээж"})))
    found = local.check("ээжтай")
    assert any(item.suggested_text == "ээжтэй" for item in found)


def test_short_case_suffix() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"өдрөөс", "өдөр"})))
    found = local.check("өдрас")
    assert any(item.suggested_text == "өдрөөс" for item in found)


def test_negative_gui() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"утгагүй"})))
    found = local.check("утгагуй")
    # listed misspelling or negative_gui both ok
    assert any(item.suggested_text == "утгагүй" for item in found)


def test_soft_sign_dative() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"сургуульд", "сургууль"})))
    found = local.check("сургуульт")
    assert any(item.suggested_text == "сургуульд" for item in found)


def test_soft_sign_genitive() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"сургуулийн", "сургууль"})))
    found = local.check("сургуульын")
    assert any(item.suggested_text == "сургуулийн" for item in found)


def test_soft_sign_accusative() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"сургуулийг", "сургууль"})))
    found = local.check("сургуульыг")
    assert any(item.suggested_text == "сургуулийг" for item in found)


def test_lah_verb_stem_from_infinitive() -> None:
    local = LanguageEngine(
        DictionaryProvider(frozenset({"туслах", "эхлэх", "дуулах", "хайрлах", "ажиллах"}))
    )
    cases = (
        ("тусладаг", "тусалдаг"),
        ("эхлэдэг", "эхэлдэг"),
        ("дууладаг", "дуулдаг"),
        ("тусласан", "тусалсан"),
        ("туслаж", "тусалж"),
        ("туслана", "тусална"),
        ("эхлэсэн", "эхэлсэн"),
    )
    for original, wanted in cases:
        found = local.check(original)
        assert any(
            item.suggested_text == wanted and item.rule_id == "lah_verb" for item in found
        ), original
    for word in ("хайрладаг", "ажилладаг", "хайрласан", "ажиллаж"):
        assert not any(item.original_text == word for item in local.check(word)), word


def test_vowel_before_verb_x_from_infinitive() -> None:
    local = LanguageEngine(
        DictionaryProvider(frozenset({"байгуулах", "явах", "бичих", "үзэх", "бодох"}))
    )
    cases = (
        ("байгуулхаар", "байгуулахаар"),
        ("байгуулхад", "байгуулахад"),
        ("явхаар", "явахаар"),
        ("бичхээр", "бичихээр"),
        ("үзхээр", "үзэхээр"),
        ("бодхоор", "бодохоор"),
        ("байгуулхгүй", "байгуулахгүй"),
        ("байгуулхдаа", "байгуулахдаа"),
    )
    for original, wanted in cases:
        found = local.check(original)
        assert any(
            item.suggested_text == wanted and item.rule_id == "vowel_before_x" for item in found
        ), original
    assert not any(item.original_text == "байгуулахаар" for item in local.check("байгуулахаар"))
    local = LanguageEngine(DictionaryProvider(frozenset({"санаачлах", "дээшлүүлэх", "явах"})))
    assert not any(item.original_text == "санаачлагатай" for item in local.check("санаачлагатай"))
    assert not any(item.original_text == "дээшлүүлэхэд" for item in local.check("дээшлүүлэхэд"))
    assert not any(item.suggested_text == "санаачлаатай" for item in local.check("санаачлагатай"))
    local = LanguageEngine(DictionaryProvider(frozenset({"боловсруулах"})))
    found = local.check("боловсруулхдоо")
    assert any(
        item.suggested_text == "боловсруулахдаа" and item.rule_id == "vowel_before_x"
        for item in found
    )


def test_erkhgui_not_rewritten_as_erehgui() -> None:
    """«эрхгүй» is noun+гүй; must not become «эрэхгүй» via vowel_before_x."""
    local = LanguageEngine(
        DictionaryProvider(frozenset({"эрхгүй", "эрх", "эрэх", "байгуулах"}))
    )
    assert not any(item.original_text == "эрхгүй" for item in local.check("эрхгүй"))
    assert not any(item.original_text == "эрхгүй" for item in local.check("тэр эрхгүй байна"))
    # Verb misspelling still fixed.
    assert any(
        item.suggested_text == "байгуулахгүй" and item.rule_id == "vowel_before_x"
        for item in local.check("байгуулхгүй")
    )


def test_palatal_case_from_stem() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"давтамж", "цаг", "багш", "ажил"})))
    cases = (
        ("давтамжыг", "давтамжийг"),
        ("давтамжын", "давтамжийн"),
        ("цагыг", "цагийг"),
        ("цагын", "цагийн"),
        ("багшыг", "багшийг"),
    )
    for original, wanted in cases:
        found = local.check(original)
        assert any(
            item.suggested_text == wanted and item.rule_id == "palatal_case" for item in found
        ), original
    assert not any(item.original_text == "ажлыг" for item in local.check("ажлыг"))
    assert not any(item.original_text == "давтамжийг" for item in local.check("давтамжийг"))
    local = LanguageEngine(DictionaryProvider(frozenset({"ус"})))
    assert not any(item.original_text == "усны" for item in local.check("усны"))
    assert not any(item.original_text == "усанд" for item in local.check("усанд"))
    assert not any(item.original_text == "уснаас" for item in local.check("уснаас"))


def test_case_forms_from_known_stems_without_full_word() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"гар", "нэр", "ном"})))
    for word in ("гарын", "нэрийн", "номын", "номноос", "номонд"):
        assert not any(item.original_text == word for item in local.check(word)), word
    found = local.check("номнаас")
    assert any(item.suggested_text == "номноос" for item in found)


def test_niy_genitive_from_stem_only() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"бие", "ээж", "нэр", "аав"})))
    cases = (
        ("биенийхээ", "биеийнхээ"),
        ("ээжнийхээ", "ээжийнхээ"),
        ("нэрнийхээ", "нэрийнхээ"),
        ("аавныхаа", "аавынхаа"),
        ("биений", "биеийн"),
    )
    for original, wanted in cases:
        found = local.check(original)
        assert any(item.suggested_text == wanted for item in found), original


def test_i_drop_from_known_stem_without_inflected_form() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"элчиг"})))
    found = local.check("элчигээ")
    assert any(item.suggested_text == "элчгээ" and item.rule_id == "i_drop" for item in found)
    found = local.check("элчигийн")
    assert any(item.suggested_text == "элчгийн" and item.rule_id == "i_drop" for item in found)
    found = local.check("элчигээр")
    assert any(item.suggested_text == "элчгээр" and item.rule_id == "i_drop" for item in found)
    found = engine.check("бичигээ")
    assert any(item.suggested_text == "бичгээ" for item in found)


def test_i_drop_after_palatal_keeps_ii() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"гарчиг", "гарчгийг"})))
    found = local.check("гарчигийг")
    assert any(item.suggested_text == "гарчгийг" and item.rule_id == "i_drop" for item in found)
    assert not any(item.suggested_text == "гарчгыг" for item in found)


def test_i_does_not_drop_before_two_consonants() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"баримт", "баримтын"})))
    found = local.check("баримтийн")
    assert any(item.suggested_text == "баримтын" for item in found)
    assert not any(item.suggested_text in {"бармтын", "бармтийн"} for item in found)


def test_long_vowel_genitive_is_ny() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"судалгаа", "судалгааны"})))
    found = local.check("судалгааний")
    assert any(item.suggested_text == "судалгааны" for item in found)
    assert not any(item.suggested_text == "судалгааын" for item in found)
    found = local.check("судалгааын")
    assert any(item.suggested_text == "судалгааны" for item in found)
    assert not any(item.original_text == "судалгааны" for item in local.check("судалгааны"))


def test_sch_converb_of_known_verb_suggests_vowel_zh() -> None:
    from app.engine.harmony import is_regular_inflection, suggest_sej_converb

    dictionary = DictionaryProvider(
        frozenset(
            {
                "багасах",
                "багасаж",
                "босох",
                "босож",
                "хасах",
                "хасаж",
                "өсөх",
                "өсөж",
            }
        )
    )
    local = LanguageEngine(dictionary)
    expected = {
        "багасч": "багасаж",
        "босч": "босож",
        "хасч": "хасаж",
        "өсч": "өсөж",
    }
    for word, want in expected.items():
        assert not is_regular_inflection(word, dictionary), word
        assert suggest_sej_converb(word, dictionary) == want, word
        found = local.check(word)
        assert any(item.suggested_text == want for item in found), (word, found)
    assert suggest_sej_converb("фысч", dictionary) is None


def test_drop_soft_sign_from_known_stem() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"дурдагдаагүй", "дурдах"})))
    found = local.check("дурьдагдаагүй")
    assert any(
        item.suggested_text == "дурдагдаагүй" and item.rule_id == "extra_soft_sign" for item in found
    )
    found = local.check("дурьдах")
    assert any(item.suggested_text == "дурдах" and item.rule_id == "extra_soft_sign" for item in found)
    assert not any(item.original_text == "дурдах" for item in local.check("дурдах"))


def test_moved_soft_sign_in_loanword() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"компьютер"})))
    found = local.check("комьпютер")
    assert any(
        item.suggested_text == "компьютер" and item.rule_id == "extra_soft_sign" for item in found
    )
    assert not any(item.original_text == "компьютер" for item in local.check("компьютер"))


def test_orchinoo_becomes_orchnoo() -> None:
    found = engine.check("орчиноо")
    assert any(item.suggested_text == "орчноо" for item in found)
    assert not any(item.suggested_text == "орчино" and item.rule_id == "doubled_letter" for item in found)


def test_ueny_becomes_ueiin() -> None:
    assert suggestion("уены", "common_misspelling") == "үеийн"


def test_n_plural_not_guud() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"ажилтнууд", "ажилтан"})))
    found = local.check("ажилтангууд")
    assert any(item.suggested_text == "ажилтнууд" for item in found)
    found = engine.check("ажилтнгууд")
    assert any(item.suggested_text == "ажилтнууд" for item in found)
    local = LanguageEngine(DictionaryProvider(frozenset({"мэргэжилтэн"})))
    found = local.check("мэргэжилтэнгүүдийн")
    assert any(item.suggested_text == "мэргэжилтнүүдийн" for item in found)
    local = LanguageEngine(DictionaryProvider(frozenset({"дүн", "дүнгүүд", "дүнгүүдийн"})))
    found = local.check("дүнүүдийн")
    assert any(item.suggested_text == "дүнгүүдийн" for item in found)
    found = local.check("дүнүүд")
    assert any(item.suggested_text == "дүнгүүд" for item in found)


def test_x_reflexive_harmony() -> None:
    local = LanguageEngine(
        DictionaryProvider(
            frozenset(
                {
                    "боловсруулах",
                    "явах",
                    "бичих",
                    "ойлгох",
                    "тавих",
                    "барих",
                    "харах",
                    "авах",
                    "гарах",
                }
            )
        )
    )
    found = local.check("боловсруулахдоо")
    assert any(item.suggested_text == "боловсруулахдаа" for item in found)
    assert not any(item.original_text == "боловсруулахдаа" for item in local.check("боловсруулахдаа"))
    assert any(item.suggested_text == "явахдаа" for item in local.check("явахдоо"))
    assert any(item.suggested_text == "бичихдээ" for item in local.check("бичихдаа"))
    assert not any(item.original_text == "явахдаа" for item in local.check("явахдаа"))
    assert not any(item.original_text == "ойлгохдоо" for item in local.check("ойлгохдоо"))
    # и is transparent: stem а/о… wins over final и → -хдаа/-хдоо, not -хдээ.
    for correct in ("тавихдаа", "барихдаа", "харахдаа", "авахдаа", "гарахдаа"):
        assert not any(item.original_text == correct for item in local.check(correct)), correct
    assert any(item.suggested_text == "тавихдаа" for item in local.check("тавихдээ"))
    assert any(item.suggested_text == "барихдаа" for item in local.check("барихдээ"))
    assert any(item.suggested_text == "харахдаа" for item in local.check("харахдээ"))
    assert any(item.suggested_text == "авахдаа" for item in local.check("авахдээ"))
    assert any(item.suggested_text == "гарахдаа" for item in local.check("гарахдээ"))


def test_n_stem_accusative_g() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"орчин", "хурал"})))
    assert not any(item.original_text == "орчинг" for item in local.check("орчинг"))
    assert not any(item.suggested_text == "орчинд" for item in local.check("орчинг"))
    found = local.check("хуралг")
    assert any(item.original_text == "хуралг" for item in found)


def test_bienee_is_kept() -> None:
    originals = {item.original_text.casefold() for item in engine.check("бие биенээ хүндэтгэж")}
    assert "биенээ" not in originals


def test_plural_harmony_back() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"номууд", "ном"})))
    found = local.check("номүүд")
    assert any(
        item.suggested_text == "номууд" and item.rule_id == "plural_harmony" for item in found
    )


def test_plural_harmony_front() -> None:
    local = LanguageEngine(DictionaryProvider(frozenset({"хүнүүд", "хүн"})))
    found = local.check("хүнууд")
    assert any(
        item.suggested_text == "хүнүүд" and item.rule_id == "plural_harmony" for item in found
    )


def test_separate_particle_shuu() -> None:
    assert suggestion("тайланшүү", "separate_particle") == "тайлан шүү"


def test_separate_particle_daa() -> None:
    assert suggestion("тиймдаа", "separate_particle") == "тийм даа"
    assert not any(item.suggested_text == "тайлан даа" for item in engine.check("тайландаа"))


def test_separate_particle_ch_and_l() -> None:
    assert suggestion("тиймл", "separate_particle") == "тийм л"
    found = engine.check("эмч ажилч")
    assert not any(item.suggested_text in {"эм ч", "ажил ч"} for item in found)


def test_school_misspellings() -> None:
    assert suggestion("учираас", "common_misspelling") == "учраас"
    assert suggestion("ажилаа", "common_misspelling") == "ажлаа"
    assert suggestion("одогоор", "common_misspelling") == "одоогоор"
    assert suggestion("маргаш", "common_misspelling") == "маргааш"
    assert suggestion("зовхон", "common_misspelling") == "зөвхөн"
    assert suggestion("хамгын", "common_misspelling") == "хамгийн"
    assert suggestion("яагаадгэвэл", "glued_words") == "яагаад гэвэл" or suggestion(
        "яагаадгэвэл", "common_misspelling"
    ) == "яагаад гэвэл"
    assert suggestion("байнадаа", "common_misspelling") == "байна даа" or suggestion(
        "байнадаа", "separate_particle"
    ) == "байна даа"


def test_correct_orthography_is_kept() -> None:
    text = "Ямар ч шаардлагатай учраас одоогоор маргааш хэрэгтэй байна шүү."
    originals = {item.original_text.casefold() for item in engine.check(text)}
    for word in ("ямар", "ч", "шаардлагатай", "учраас", "одоогоор", "маргааш", "хэрэгтэй"):
        assert word not in originals
