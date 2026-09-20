from __future__ import annotations

import uuid

from app.engine.dictionary import (
    DictionaryProvider,
    _FREQ_TRUST,
    _collapse_duplicate_letters,
    _edit_distance,
    _is_adjacent_swap,
)
from app.engine.harmony import (
    is_regular_inflection,
    suggest_i_drop,
    suggest_lah_verb,
    suggest_vowel_before_x,
    suggest_x_reflexive,
    suggest_n_plural,
    suggest_n_plural_g,
    suggest_negative_gui,
    suggest_niy_genitive,
    suggest_sej_converb,
    suggest_palatal_case,
    suggest_plural_harmony,
    suggest_short_case_suffix,
    suggest_drop_soft_sign,
    suggest_soft_sign_dative,
    suggest_soft_sign_genitive,
    suggest_suffix_harmony,
    is_broken_case_form,
    drops_stem_i_before_cluster,
)
from app.engine.misspellings import lookup_misspelling
from app.engine.models import Category, Correction, Severity, Source
from app.engine.style import OFFICIAL_REPLACEMENTS
from app.engine.text import Token, is_cyrillic_letter

_EXPLANATIONS = {
    "doubled_letter": "Давхардсан үсгийг хассан зөв хувилбар.",
    "nearby_spelling": "Толь дахь ойролцоо үг. Үсэг дутуу, илүүц эсвэл буруу байж болзошгүй.",
    "common_misspelling": "Түгээмэл зөв бичгийн алдаа.",
    "suffix_harmony": "Тийн ялгалын нөхцөл эгшгийн эв нэгдлийг дагана.",
    "short_case_suffix": "Тийн ялгалын нөхцөлийн эгшиг урт бичигдэнэ (аас, ээс, оос, өөс).",
    "negative_gui": "Үгүйсгэх нөхцөл -гүй-г ү үсгээр бичнэ.",
    "extra_suffix": "Үгийн төгсгөлд илүүц үсэг орсон байна.",
    "unknown_word": "Монгол үг биш, эсвэл буруу бичсэн байна. Засах санал алга.",
    "plural_harmony": "Олноо нэрлэх -ууд/-үүд эгшгийн эв нэгдлийг дагана.",
    "n_plural": "-тан/-тэн нэр үгийн олон тоонд сүүлийн эгшиг орхигдоно (ажилтангууд → ажилтнууд).",
    "n_plural_g": "Н-ээр төгссөн үгийн олон тоонд -гууд/-гүүд нэмэгдэнэ (дүнүүд → дүнгүүд).",
    "reflexive_harmony": "Үйл үгийн -хдаа/-хдээ/-хдоо/-хдөө эгшгийн эв нэгдлийг дагана.",
    "i_drop": "Нөхцөл нэмэгдэхэд үндэсний и эгшиг орхигдоно.",
    "n_genitive": "Эгшгээр төгссөн үгийн харьяалах -ийн/-ын гэж бичигдэнэ.",
    "sej_converb": "С-ийн дараа үйл үгийн хэв нь -аж/-эж/-ож/-өж гэж бичигдэнэ (багасч → багасаж).",
    "lah_verb": "Үйл үгийн -лах нөхцөлд л болон эгшгийн байр солигдоно (туслах → тусалдаг).",
    "vowel_before_x": "Үйл үгийн х-ийн өмнө эгшиг бичигдэнэ (байгуулах → байгуулахаар).",
    "soft_sign_dative": "Ь-ийн дараа өгөх тийн ялгал -д гэж бичигдэнэ.",
    "soft_sign_genitive": "Ь-ийн дараа харьяалах, заах тийн ялгал -ийн/-ийг гэж бичигдэнэ.",
    "extra_soft_sign": "Энэ үгэнд ь хэрэггүй. Толь дахь хэлбэрээр бичнэ.",
    "palatal_case": "Г, ж, ш, ч-ийн дараа харьяалах, заах тийн ялгал -ийн/-ийг гэж бичигдэнэ.",
    "glued_auxiliary": "Туслах үйл үг «байна/болно»-г тусад нь бичнэ.",
    "glued_question_particle": "Асуух «уу/үү»-г тусад нь бичнэ.",
    "glued_directive": "Чиглэлийн «руу/рүү»-г тусад нь бичнэ.",
    "glued_words": "Хоёр үг наалдсан байна. Зай эсвэл таслал дутуу.",
    "separate_particle": "Энэ нөхцөл, өгүүлэхүүнийг тусад нь бичнэ.",
}


def _is_cyrillic_word(word: str) -> bool:
    letters = [ch for ch in word if ch.isalpha()]
    return bool(letters) and all(is_cyrillic_letter(ch) for ch in letters)


def _apply_case(original: str, suggested: str) -> str:
    if not suggested:
        return suggested
    letters = [ch for ch in original if ch.isalpha()]
    if letters and all(ch.isupper() for ch in letters):
        return suggested.upper()
    if original[:1].isupper():
        head, sep, tail = suggested.partition(" ")
        cased = head[:1].upper() + head[1:]
        return cased + sep + tail
    return suggested


_VOWELS = frozenset("аэиоуөүяёеюы")
_BAD_START = frozenset("ыьъ")
_BAD_SEQ = ("йы", "йь", "ъы", "ыъ")


def _is_implausible(word: str) -> bool:
    """Letter sequences that do not occur in Mongolian words."""
    folded = word.casefold()
    letters = [ch for ch in folded if ch.isalpha()]
    if len(letters) < 2:
        return False
    if letters[0] in _BAD_START:
        return True
    if any(seq in folded for seq in _BAD_SEQ):
        return True
    # No vowel at all (рр, рш, …) — not a Mongolian word form.
    if not any(ch in _VOWELS for ch in letters):
        return True
    if len(letters) < 3:
        return False
    run = 0
    for ch in letters:
        if ch in _VOWELS:
            run = 0
            continue
        run += 1
        if run >= 5:
            return True
    return False


def _looks_like_name(word: str) -> bool:
    return word[:1].isupper() and not _is_implausible(word)


_AUX_OR_PARTICLE_TAILS = frozenset(
    {
        "байна",
        "байгаа",
        "байсан",
        "байх",
        "байдаг",
        "байлаа",
        "байжээ",
        "болно",
        "болох",
        "уу",
        "үү",
        "руу",
        "рүү",
        "даа",
        "шүү",
    }
)


def _has_wordlist_stem(word: str, dictionary: DictionaryProvider) -> bool:
    """True when word looks like a known stem + inflection — not stem + free word glued on."""
    folded = word.casefold()
    for n in range(len(folded) - 1, 4, -1):
        stem, rest = folded[:n], folded[n:]
        if not dictionary.in_wordlist(stem):
            continue
        if rest in _AUX_OR_PARTICLE_TAILS:
            continue
        if len(rest) >= 4 and (dictionary.in_wordlist(rest) or dictionary.contains(rest)):
            continue
        return True
    return False


_RULE_FIRST = frozenset(
    {
        "negative_gui",
        "soft_sign_dative",
        "soft_sign_genitive",
        "extra_soft_sign",
        "palatal_case",
        "suffix_harmony",
        "short_case_suffix",
        "plural_harmony",
        "n_plural",
        "n_plural_g",
        "reflexive_harmony",
        "i_drop",
        "n_genitive",
        "sej_converb",
        "lah_verb",
        "vowel_before_x",
        "extra_suffix",
    }
)

# Do not "correct" wiki/legal-established spellings with these school pedantry rules.
_ESTABLISHED_KEEP = frozenset(
    {
        "extra_soft_sign",
        "lah_verb",
        "short_case_suffix",
        "soft_sign_dative",
        "soft_sign_genitive",
    }
)


def _confidence(rule_id: str) -> float:
    if rule_id == "common_misspelling":
        return 0.9
    if rule_id.startswith(("glued_", "separate_")):
        return 0.92
    if rule_id == "unknown_word":
        return 0.5
    if rule_id == "nearby_spelling":
        return 0.78
    if rule_id == "doubled_letter":
        return 0.7
    return 0.86


def _usable_suggestion(original: str, item: str) -> bool:
    return (
        not lookup_misspelling(item)
        and not is_broken_case_form(item)
        and not drops_stem_i_before_cluster(original, item)
        and not _bad_sch_neighbor(original, item)
    )


def _bad_sch_neighbor(original: str, suggestion: str) -> bool:
    """Reject junk neighbors for -сч forms (хүсч→хүч, гасч→гарч, тааласч→таалал).

    Legitimate fixes keep the stem and end in a converb -*ж (хүсэж, багасаж, уншиж).
    """
    folded = original.casefold()
    other = suggestion.casefold()
    if not folded.endswith("сч") or len(folded) < 3:
        return False
    stem_sc = folded[:-1]  # хүс / багас
    stem = folded[:-2]  # хү / бага / унш
    converb_tails = ("ааж", "ээж", "оож", "өөж", "аж", "эж", "ож", "өж", "иж", "ж")
    if other.endswith(converb_tails) and (
        other.startswith(stem_sc)
        or (len(stem) >= 2 and other.startswith(stem))
    ):
        return False
    return True


def check_spelling(tokens: list[Token], dictionary: DictionaryProvider) -> list[Correction]:
    """Spell-check tokens, caching decisions by folded form.

    Long legal documents repeat the same word thousands of times; without a
    cache each occurrence re-runs expensive suggest_many and hangs the UI.
    Cap how many times each unique misspelling is marked so the editor stays
    usable on ~400k-character statutes.
    """
    corrections: list[Correction] = []
    preferred = {
        token.text.casefold() for token in tokens if dictionary.in_wordlist(token.text)
    }
    # folded -> None (no mark) | ("hit", suggested, rule_id, extras) | ("unknown",)
    cache: dict[str, tuple | None] = {}
    form_counts: dict[str, int] = {}
    _MAX_PER_FORM = 5
    _MAX_TOTAL = 800
    # Neighbor search is the slow path. On long docs skip it entirely — orthography
    # rules + unknown marks are enough, and suggest_many was dominating wall time.
    n_tokens = len(tokens)
    if n_tokens > 3_000:
        nearby_budget = 0
    elif n_tokens > 2_000:
        nearby_budget = 20
    else:
        nearby_budget = 120
    budget = {"nearby": nearby_budget}
    for token in tokens:
        if len(corrections) >= _MAX_TOTAL:
            break
        if not _is_cyrillic_word(token.text):
            continue
        folded = token.text.casefold()
        # Names depend on capitalization — do not reuse a lowercase decision.
        cache_key = folded if not _looks_like_name(token.text) else f"^{token.text}"
        if cache_key in cache:
            decision = cache[cache_key]
        else:
            decision = _spelling_decision(token.text, dictionary, preferred, budget)
            cache[cache_key] = decision
        if decision is None:
            continue
        seen = form_counts.get(folded, 0)
        if seen >= _MAX_PER_FORM:
            continue
        form_counts[folded] = seen + 1
        kind = decision[0]
        if kind == "unknown":
            corrections.append(_unknown(token))
        elif kind == "hit":
            _, suggested, rule_id, extras = decision
            # Never flag case-only differences (Үндэсний ↔ үндэсний).
            if suggested.casefold() == token.text.casefold():
                continue
            corrections.append(_hit(token, suggested, rule_id, extras))
    return corrections


def _spelling_decision(
    word: str,
    dictionary: DictionaryProvider,
    preferred: set[str],
    budget: dict[str, int] | None = None,
) -> tuple | None:
    misspelled = lookup_misspelling(word)
    if misspelled:
        extras: list[str] = []
        if budget is None or budget.get("nearby", 0) > 0:
            if budget is not None:
                budget["nearby"] -= 1
            extras = [
                item
                for item in dictionary.suggest_many(word, preferred=preferred, limit=3)
                if item != misspelled and _usable_suggestion(word, item)
            ]
        return ("hit", misspelled, "common_misspelling", extras)
    if "-" in word:
        return None
    if dictionary.contains(word):
        # Hunspell sometimes accepts wrong -сч school forms (үсч, загасч).
        sej = suggest_sej_converb(word, dictionary)
        if sej and sej.casefold() != word.casefold():
            return ("hit", sej, "sej_converb", [])
        if len(word) >= 4:
            reflexive = suggest_x_reflexive(word, dictionary)
            if reflexive:
                return ("hit", reflexive, "reflexive_harmony", [])
        return None
    if word.casefold() in OFFICIAL_REPLACEMENTS:
        return None
    result = None
    alts: list[str] = []
    if len(word) >= 4:
        result = _suggest(word, dictionary)
        # Harmony rules must propose an attested form — never invent junk like мөрийийн.
        # sej_converb may derive багасаж from known багасах even if the converb
        # itself is missing from a minimal test dictionary.
        if (
            result
            and result[1] in _RULE_FIRST
            and result[1] != "sej_converb"
            and not (
                dictionary.contains(result[0]) or dictionary.in_wordlist(result[0])
            )
        ):
            result = None
        # Keep established legal/wiki spellings (дараахь, батласан, …).
        if result and result[1] in _ESTABLISHED_KEEP and dictionary.prefers_established(word):
            result = None
        if result and result[1] in _RULE_FIRST:
            # Orthography rule is enough — skip expensive neighbor extras.
            alts = [result[0]]
        elif not _is_implausible(word):
            # Long sealed docs exhaust the nearby budget; still accept regular
            # / established forms instead of dumping them as unknown_word.
            if len(word) >= 3 and (
                is_regular_inflection(word, dictionary)
                or dictionary.is_frequent_inflection(word)
                or dictionary.prefers_established(word)
            ):
                return None
            if budget is not None and budget.get("nearby", 0) <= 0:
                return ("unknown",)
            if budget is not None:
                budget["nearby"] -= 1
            alts = [
                item
                for item in dictionary.suggest_many(word, preferred=preferred, limit=3)
                if _usable_suggestion(word, item)
            ]
            if alts:
                primary = alts[0]
                # Frequent real forms (хүсч) must not lose to shorter neighbors (хүч).
                if dictionary.prefers_established(word):
                    return None
                if dictionary.prefers_established(word, primary):
                    return None
                doubled = any(
                    primary in (variant, variant.casefold())
                    for variant in _collapse_duplicate_letters(word.casefold())
                )
                result = (primary, "doubled_letter" if doubled else "nearby_spelling")
                alts = _confident_alts(word, alts, result, dictionary)
    elif word.casefold().endswith("сч"):
        # өсч (3 letters) still needs the school converb fix.
        sej = suggest_sej_converb(word, dictionary)
        if sej:
            result = (sej, "sej_converb")
            alts = [sej]
    if (
        not (result and result[1] in _RULE_FIRST)
        and len(word) >= 3
        and (
            is_regular_inflection(word, dictionary)
            or dictionary.is_frequent_inflection(word)
        )
    ):
        return None
    if alts and not (result and result[0] == word.casefold()):
        if result and result[1] == "nearby_spelling" and dictionary.prefers_established(word):
            return None
        if not _is_implausible(word) or (result and result[1] != "nearby_spelling"):
            rule_id = result[1] if result else "nearby_spelling"
            return ("hit", alts[0], rule_id, alts[1:])
    if dictionary.prefers_established(word):
        return None
    if _is_implausible(word) or (
        len(word) >= 3
        and dictionary.has_hunspell
        and not _looks_like_name(word)
        and not _has_wordlist_stem(word, dictionary)
    ):
        return ("unknown",)
    return None


def _confident_alts(
    original: str,
    alts: list[str],
    result: tuple[str, str] | None,
    dictionary: DictionaryProvider,
) -> list[str]:
    """Do not flag a real-looking word just because a similar dictionary word exists."""
    if not alts:
        return []
    rule = result[1] if result else "nearby_spelling"
    if rule in _RULE_FIRST or rule in {"doubled_letter", "common_misspelling"}:
        return alts
    if _is_implausible(original):
        return alts
    folded = original.casefold()
    for item in alts:
        other = item.casefold()
        dist = _edit_distance(folded, other)
        swapped = _is_adjacent_swap(folded, other)
        if dist != 1 and not swapped:
            prefix = 0
            for a, b in zip(folded, other, strict=False):
                if a != b:
                    break
                prefix += 1
            frequent = dictionary.wiki_frequency(item) >= _FREQ_TRUST
            long_typo = len(folded) >= 6
            if not (
                long_typo
                and frequent
                and prefix >= 3
                and (dist == 2 or dist == 3)
            ):
                continue
        if len(folded) == len(other) and folded[1:] == other[1:] and folded[:1] != other[:1]:
            if {folded[:1], other[:1]} not in ({"о", "ө"}, {"у", "ү"}):
                continue
        if (
            len(folded) == len(other)
            and folded[:-1] == other[:-1]
            and {folded[-1:], other[-1:]} <= {"г", "д", "н"}
        ):
            continue
        if dictionary.in_seed(item):
            return alts
        if len(folded) >= 5 and dictionary.in_wordlist(item):
            return alts
        if len(folded) >= 5 and dictionary.contains(item) and (
            swapped
            or _vowel_edit_only(folded, other)
            or dictionary.wiki_frequency(item) >= _FREQ_TRUST
        ):
            return alts
    return []


def _vowel_edit_only(original: str, candidate: str) -> bool:
    """Nearby Hunspell hits that only change a vowel, not a consonant (лага → лаа)."""
    if abs(len(original) - len(candidate)) > 1:
        return False
    if len(original) == len(candidate):
        diffs = [(a, b) for a, b in zip(original, candidate, strict=True) if a != b]
        return len(diffs) == 1 and diffs[0][0] in _VOWELS and diffs[0][1] in _VOWELS
    longer, shorter = (original, candidate) if len(original) > len(candidate) else (candidate, original)
    for i, ch in enumerate(longer):
        if longer[:i] + longer[i + 1 :] == shorter:
            return ch in _VOWELS
    return False


def _suggest(word: str, dictionary: DictionaryProvider) -> tuple[str, str] | None:
    negative = suggest_negative_gui(word, dictionary)
    if negative:
        return negative, "negative_gui"
    dative = suggest_soft_sign_dative(word, dictionary)
    if dative:
        return dative, "soft_sign_dative"
    genitive = suggest_soft_sign_genitive(word, dictionary)
    if genitive:
        return genitive, "soft_sign_genitive"
    extra_soft = suggest_drop_soft_sign(word, dictionary)
    if extra_soft:
        return extra_soft, "extra_soft_sign"
    palatal = suggest_palatal_case(word, dictionary)
    if palatal:
        return palatal, "palatal_case"
    harmony = suggest_suffix_harmony(word, dictionary)
    if harmony:
        return harmony, "suffix_harmony"
    shortened = suggest_short_case_suffix(word, dictionary)
    if shortened:
        return shortened, "short_case_suffix"
    plural = suggest_plural_harmony(word, dictionary)
    if plural:
        return plural, "plural_harmony"
    n_plural = suggest_n_plural(word, dictionary)
    if n_plural:
        return n_plural, "n_plural"
    n_g = suggest_n_plural_g(word, dictionary)
    if n_g:
        return n_g, "n_plural_g"
    reflexive = suggest_x_reflexive(word, dictionary)
    if reflexive:
        return reflexive, "reflexive_harmony"
    dropped = suggest_i_drop(word, dictionary)
    if dropped:
        return dropped, "i_drop"
    niy = suggest_niy_genitive(word, dictionary)
    if niy:
        return niy, "n_genitive"
    sej = suggest_sej_converb(word, dictionary)
    if sej:
        return sej, "sej_converb"
    lah = suggest_lah_verb(word, dictionary)
    if lah:
        return lah, "lah_verb"
    before_x = suggest_vowel_before_x(word, dictionary)
    if before_x:
        return before_x, "vowel_before_x"
    extra = _suggest_extra_suffix(word, dictionary)
    if extra:
        return extra, "extra_suffix"
    return None


_FINISHED = ("сан", "сэн", "сон", "сөн", "на", "нэ", "но", "нө")
_JUNK_TAIL = frozenset({"эн", "ан", "на", "ээ", "аа"})


def _suggest_extra_suffix(word: str, dictionary: DictionaryProvider) -> str | None:
    folded = word.casefold()
    for n in (3, 2, 1):
        if len(folded) < 5 + n:
            continue
        stem, tail = folded[:-n], folded[-n:]
        if n > 1 and tail not in _JUNK_TAIL:
            continue
        if n == 1 and tail not in {"н", "э", "а"}:
            continue
        if stem.endswith(_FINISHED) and dictionary.contains(stem):
            return stem
    return None


def _unknown(token: Token) -> Correction:
    return Correction(
        id=str(uuid.uuid4()),
        category=Category.SPELLING,
        original_text=token.text,
        suggested_text="",
        explanation=_EXPLANATIONS["unknown_word"],
        confidence=_confidence("unknown_word"),
        start=token.start,
        end=token.end,
        source=Source.DICTIONARY,
        rule_id="unknown_word",
        severity=Severity.ERROR,
    )


def _hit(
    token: Token,
    suggested: str,
    rule_id: str,
    extras: list[str] | None = None,
) -> Correction:
    primary = _apply_case(token.text, suggested)
    more = [_apply_case(token.text, item) for item in extras or [] if item != suggested]
    return Correction(
        id=str(uuid.uuid4()),
        category=Category.SPELLING,
        original_text=token.text,
        suggested_text=primary,
        explanation=_EXPLANATIONS.get(rule_id, _EXPLANATIONS["nearby_spelling"]),
        confidence=_confidence(rule_id),
        start=token.start,
        end=token.end,
        source=Source.DICTIONARY if rule_id != "common_misspelling" else Source.RULE,
        rule_id=rule_id,
        severity=Severity.ERROR,
        suggestions=more,
    )
