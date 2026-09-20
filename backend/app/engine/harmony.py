from __future__ import annotations

from app.engine.dictionary import DictionaryProvider

FRONT = frozenset("эөүеи")
BACK = frozenset("аоуяёюы")

# School orthography: suffix vowels follow the last stem vowel (эв нэгдэл).
_ABLATIVE = {
    "а": "аас",
    "я": "аас",
    "у": "аас",
    "ы": "аас",
    "э": "ээс",
    "е": "ээс",
    "и": "ээс",
    "ү": "ээс",
    "о": "оос",
    "ё": "оос",
    "ө": "өөс",
}
_INSTRUMENTAL = {
    "а": "аар",
    "я": "аар",
    "у": "аар",
    "ы": "аар",
    "э": "ээр",
    "е": "ээр",
    "и": "ээр",
    "ү": "ээр",
    "о": "оор",
    "ё": "оор",
    "ө": "өөр",
}
_GENITIVE = {
    "а": "ын",
    "я": "ын",
    "у": "ын",
    "ы": "ын",
    "о": "ын",
    "ё": "ын",
    "э": "ийн",
    "е": "ийн",
    "и": "ийн",
    "ү": "ийн",
    "ө": "ийн",
}
_ACCUSATIVE = {
    "а": "ыг",
    "я": "ыг",
    "у": "ыг",
    "ы": "ыг",
    "о": "ыг",
    "ё": "ыг",
    "э": "ийг",
    "е": "ийг",
    "и": "ийг",
    "ү": "ийг",
    "ө": "ийг",
}
_COMITATIVE = {
    "а": "тай",
    "я": "тай",
    "у": "тай",
    "ы": "тай",
    "о": "той",
    "ё": "той",
    "э": "тэй",
    "е": "тэй",
    "и": "тэй",
    "ү": "тэй",
    "ө": "тэй",
}
_DIRECTIVE = {
    "а": "руу",
    "я": "руу",
    "у": "руу",
    "ы": "руу",
    "о": "руу",
    "ё": "руу",
    "э": "рүү",
    "е": "рүү",
    "и": "рүү",
    "ү": "рүү",
    "ө": "рүү",
}

_DATIVE_ND = {
    "а": "анд",
    "я": "анд",
    "у": "анд",
    "ы": "анд",
    "о": "онд",
    "ё": "онд",
    "э": "энд",
    "е": "энд",
    "и": "энд",
    "ө": "өнд",
    "ү": "өнд",
}
_ABLATIVE_N = {
    "а": "наас",
    "я": "наас",
    "у": "наас",
    "ы": "наас",
    "о": "ноос",
    "ё": "ноос",
    "э": "нээс",
    "е": "нээс",
    "и": "нээс",
    "ө": "нөөс",
    "ү": "нөөс",
}
_INSTRUMENTAL_N = {
    "а": "наар",
    "я": "наар",
    "у": "наар",
    "ы": "наар",
    "о": "ноор",
    "ё": "ноор",
    "э": "нээр",
    "е": "нээр",
    "и": "нээр",
    "ө": "нөөр",
    "ү": "нөөр",
}
_POSSESSIVE = {
    "а": "хаа",
    "я": "хаа",
    "у": "хаа",
    "ы": "хаа",
    "о": "хоо",
    "ё": "хоо",
    "э": "хээ",
    "е": "хээ",
    "и": "хээ",
    "ө": "хөө",
    "ү": "хөө",
}
_REFLEXIVE = {
    "а": "аа",
    "я": "аа",
    "у": "аа",
    "ы": "аа",
    "о": "оо",
    "ё": "оо",
    "э": "ээ",
    "е": "ээ",
    "и": "ээ",
    "ө": "өө",
    "ү": "өө",
}

_N_CONNECTING = frozenset({*_ABLATIVE_N.values(), *_INSTRUMENTAL_N.values()})

_SUFFIX_GROUPS: tuple[tuple[tuple[str, ...], dict[str, str]], ...] = (
    (("нөөс", "ноос", "нээс", "наас"), _ABLATIVE_N),
    (("нөөр", "ноор", "нээр", "наар"), _INSTRUMENTAL_N),
    (("өөс", "оос", "ээс", "аас"), _ABLATIVE),
    (("өөр", "оор", "ээр", "аар"), _INSTRUMENTAL),
    (("ийн", "ын"), _GENITIVE),
    (("ийг", "ыг"), _ACCUSATIVE),
    (("тэй", "тай", "той", "төй"), _COMITATIVE),
    (("рүү", "руу"), _DIRECTIVE),
)

_VERBAL_DATIVE = {
    "а": "ад",
    "я": "ад",
    "у": "ад",
    "ы": "ад",
    "о": "од",
    "ё": "од",
    "э": "эд",
    "е": "эд",
    "и": "эд",
    "ө": "өд",
    "ү": "өд",
}

_NOMINALIZERS = (
    ("лага", "лах"),
    ("лэг", "лэх"),
    ("лого", "лох"),
    ("лөг", "лөх"),
)

_PEEL_GROUPS: tuple[tuple[tuple[str, ...], dict[str, str]], ...] = (
    (tuple(dict.fromkeys(_POSSESSIVE.values())), _POSSESSIVE),
    (tuple(dict.fromkeys(_DATIVE_ND.values())), _DATIVE_ND),
    (tuple(dict.fromkeys(_ABLATIVE_N.values())), _ABLATIVE_N),
    (tuple(dict.fromkeys(_INSTRUMENTAL_N.values())), _INSTRUMENTAL_N),
    *_SUFFIX_GROUPS,
    (tuple(dict.fromkeys(_REFLEXIVE.values())), _REFLEXIVE),
)

_SHORT_GROUPS: tuple[tuple[tuple[str, ...], dict[str, str]], ...] = (
    (("өс", "ос", "эс", "ас"), _ABLATIVE),
    (("өр", "ор", "эр", "ар"), _INSTRUMENTAL),
)


def last_vowel(word: str) -> str | None:
    for ch in reversed(word.casefold()):
        if ch in "аэиоуөүяёеюы":
            return ch
    return None


def is_broken_case_form(word: str) -> bool:
    """Case spelling that a school rule would reject (гарчгыг, судалгааын)."""
    folded = word.casefold()
    if folded.endswith(("ааын", "ээийн", "ооын", "өөийн")):
        return True
    if len(folded) >= 4 and folded.endswith("ыг") and folded[-3] in "гжшч":
        return True
    return False


def drops_stem_i_before_cluster(original: str, candidate: str) -> bool:
    """баримтийн → бармтын: и does not drop before two consonants."""
    folded = original.casefold()
    other = candidate.casefold()
    vowels = "аэиоуөүяёеюы"
    for i, ch in enumerate(folded):
        if ch != "и" or i < 1 or i + 2 >= len(folded):
            continue
        if folded[i + 1] in vowels or folded[i + 2] in vowels:
            continue
        without = folded[:i] + folded[i + 1 :]
        if other == without or other.startswith(without[: max(4, i + 2)]):
            return True
    return False


def last_harmony_vowel(word: str) -> str | None:
    """и is transparent: баримт follows а, not the и before мт."""
    seen_i: str | None = None
    for ch in reversed(word.casefold()):
        if ch == "и":
            if seen_i is None:
                seen_i = ch
            continue
        if ch in "аэоуөүяёеюы":
            return ch
    return seen_i


def question_particle(word: str) -> str | None:
    vowel = last_vowel(word)
    if vowel in FRONT:
        return "үү"
    if vowel in BACK:
        return "уу"
    return None


def ve_particle(word: str) -> str | None:
    vowel = last_vowel(word)
    if vowel in FRONT:
        return "бэ"
    if vowel in BACK:
        return "вэ"
    return None


def suggest_suffix_harmony(word: str, dictionary: DictionaryProvider) -> str | None:
    folded = word.casefold()
    for group, mapping in _SUFFIX_GROUPS:
        matched = next(
            (suffix for suffix in sorted(group, key=len, reverse=True) if folded.endswith(suffix)),
            None,
        )
        if matched is None:
            continue
        if len(folded) - len(matched) < 3:
            continue
        stem = folded[: -len(matched)]
        if (mapping is _GENITIVE or mapping is _ACCUSATIVE) and stem[-1:] in "гжшч":
            continue
        wanted = mapping.get(last_harmony_vowel(stem) or last_vowel(stem) or "")
        if not wanted or wanted == matched:
            continue
        candidate = stem + wanted
        if dictionary.contains(candidate):
            return candidate
        if matched in _N_CONNECTING and _known_stem(stem, dictionary):
            return candidate
    return None


def suggest_palatal_case(word: str, dictionary: DictionaryProvider) -> str | None:
    """After г, ж, ш, ч the genitive/accusative is -ийн/-ийг (давтамжыг → давтамжийг)."""
    folded = word.casefold()
    for wrong, right in (("ыг", "ийг"), ("ын", "ийн")):
        if not folded.endswith(wrong) or len(folded) < len(wrong) + 2:
            continue
        stem = folded[: -len(wrong)]
        if stem[-1:] not in "гжшч":
            continue
        candidate = stem + right
        if candidate == folded:
            continue
        if _known_stem(stem, dictionary) or dictionary.contains(candidate):
            return candidate
    return None


def suggest_short_case_suffix(word: str, dictionary: DictionaryProvider) -> str | None:
    folded = word.casefold()
    # Already a long suffix — handled elsewhere.
    if any(folded.endswith(suffix) for group, _ in _SUFFIX_GROUPS for suffix in group):
        return None
    for group, mapping in _SHORT_GROUPS:
        matched = next((suffix for suffix in group if folded.endswith(suffix)), None)
        if matched is None:
            continue
        if len(folded) - len(matched) < 3:
            continue
        stem = folded[: -len(matched)]
        wanted = mapping.get(last_vowel(stem) or "")
        if not wanted:
            continue
        candidate = stem + wanted
        if dictionary.contains(candidate):
            return candidate
    return None


def _known_stem(word: str, dictionary: DictionaryProvider) -> bool:
    return dictionary.contains(word) or dictionary.in_wordlist(word)


def _known_derived_stem(word: str, dictionary: DictionaryProvider) -> bool:
    """санаачлага ← санаачлах; keep Xлагатай when the verb exists."""
    for nom, verb_tail in _NOMINALIZERS:
        if word.endswith(nom) and len(word) > len(nom) + 2:
            if _known_stem(word[: -len(nom)] + verb_tail, dictionary):
                return True
    return False


def _peel_harmonic_suffix(folded: str) -> str | None:
    if len(folded) > 3 and folded.endswith("г"):
        stem = folded[:-1]
        if stem[-1:] in "н" or stem[-1:] in _VOWELS:
            return stem
    if len(folded) > 3 and folded.endswith("ны"):
        stem = folded[:-2]
        if stem[-1:] in "ндс" and last_vowel(stem) in BACK:
            return stem
    if len(folded) > 4 and folded.endswith("ний"):
        stem = folded[:-3]
        if stem[-1:] in "ндс" and last_vowel(stem) in FRONT:
            return stem
    if len(folded) > 4:
        for suffix in dict.fromkeys(_VERBAL_DATIVE.values()):
            if not folded.endswith(suffix):
                continue
            stem = folded[: -len(suffix)]
            if (
                stem.endswith("х")
                and len(stem) >= 4
                and _VERBAL_DATIVE.get(last_vowel(stem) or "") == suffix
            ):
                return stem
    options: list[tuple[str, dict[str, str]]] = []
    for group, mapping in _PEEL_GROUPS:
        for suffix in group:
            options.append((suffix, mapping))
    options.sort(key=lambda item: -len(item[0]))
    for suffix, mapping in options:
        if not folded.endswith(suffix) or len(folded) - len(suffix) < 2:
            continue
        stem = folded[: -len(suffix)]
        if (mapping is _GENITIVE or mapping is _ACCUSATIVE) and stem[-1:] in "гжшч":
            if suffix in ("ын", "ыг"):
                continue
            if suffix in ("ийн", "ийг"):
                return stem
        if mapping.get(last_vowel(stem) or "") == suffix:
            return stem
    return None


def is_regular_inflection(word: str, dictionary: DictionaryProvider) -> bool:
    """Known stem plus one or more matching school suffixes (усны, усанд, биеийнхээ)."""
    folded = word.casefold()
    if _lah_correct_form(folded, dictionary) == folded:
        return True
    if _kept_x_reflexive(folded, dictionary):
        return True
    if _kept_sch_converb(folded, dictionary):
        return True
    remaining = folded
    peeled = False
    for _ in range(3):
        stem = _peel_harmonic_suffix(remaining)
        if stem is None:
            return False
        remaining = stem
        peeled = True
        if _known_stem(remaining, dictionary) or _known_derived_stem(remaining, dictionary):
            return True
    return peeled and (
        _known_stem(remaining, dictionary) or _known_derived_stem(remaining, dictionary)
    )


_SCH_INFINITIVE = {
    "а": "ах",
    "я": "ах",
    "у": "ах",
    "ы": "ах",
    "ю": "ах",
    "э": "эх",
    "е": "эх",
    "и": "эх",
    "о": "ох",
    "ё": "ох",
    "ө": "өх",
    "ү": "өх",
}


def _sch_infinitive(folded: str) -> str | None:
    """багасч ← багасах: connecting vowel drops and ж is written ч after с."""
    if not folded.endswith("сч") or len(folded) < 3:
        return None
    stem = folded[:-2]
    if not stem or not stem[-1:].isalpha():
        return None
    tail = _SCH_INFINITIVE.get(last_vowel(stem) or "")
    if not tail:
        return None
    return stem + "с" + tail


def _kept_sch_converb(folded: str, dictionary: DictionaryProvider) -> bool:
    infinitive = _sch_infinitive(folded)
    return bool(infinitive and _known_stem(infinitive, dictionary))


# Converb after с: school form is -аж/-эж/-ож/-өж, not bare -ч (хүсч → хүсэж).
_SEJ_CONVERB = {
    "а": "аж",
    "я": "аж",
    "у": "аж",
    "ы": "аж",
    "ю": "аж",
    "о": "ож",
    "ё": "ож",
    "э": "эж",
    "е": "эж",
    "и": "эж",
    "ү": "эж",
    "ө": "өж",
}

_SEJ_INFINITIVE = {
    "а": "ах",
    "я": "ах",
    "у": "ах",
    "ы": "ах",
    "ю": "ах",
    "о": "ох",
    "ё": "ох",
    "э": "эх",
    "е": "эх",
    "и": "эх",
    "ү": "эх",
    "ө": "өх",
}


def suggest_sej_converb(word: str, dictionary: DictionaryProvider) -> str | None:
    """хүсч → хүсэж when -сч is not the legitimate -сах verb shortening."""
    folded = word.casefold()
    if not folded.endswith("сч") or len(folded) < 4:
        return None
    # багасч ← багасах stays as-is.
    if _kept_sch_converb(folded, dictionary):
        return None
    stem = folded[:-1]  # хүсч → хүс (drop ч)
    if not stem.endswith("с") or len(stem) < 2:
        return None
    base = stem[:-1]
    vowel = last_harmony_vowel(base) or last_vowel(base)
    sej = _SEJ_CONVERB.get(vowel or "")
    if not sej:
        return None
    candidate = stem + sej  # хүс + эж
    if candidate == folded:
        return None
    if dictionary.contains(candidate) or dictionary.in_wordlist(candidate):
        return candidate
    inf = _SEJ_INFINITIVE.get(vowel or "")
    if inf and _known_stem(stem + inf, dictionary):
        return candidate
    return None


def suggest_niy_genitive(word: str, dictionary: DictionaryProvider) -> str | None:
    """Vowel/consonant stem genitive is -ийн/-ын, not -ний/-ны."""
    folded = word.casefold()
    tail = ""
    core = folded
    for poss in ("хөө", "хоо", "хээ", "хаа"):
        if core.endswith(poss) and len(core) > len(poss) + 2:
            tail = poss
            core = core[: -len(poss)]
            break
    for wrong, right in (
        ("ааын", "ааны"),
        ("ээийн", "ээний"),
        ("ооын", "ооны"),
        ("өөийн", "өөний"),
    ):
        if core.endswith(wrong) and len(core) > len(wrong) + 1:
            candidate = core[: -len(wrong)] + right + tail
            if candidate != folded:
                return candidate
    for wrong in ("ний", "ны"):
        idx = core.rfind(wrong)
        if idx < 2 or idx + len(wrong) != len(core):
            continue
        stem = core[:idx]
        if not _known_stem(stem, dictionary):
            continue
        if stem[-1:] in "ндс":
            continue
        if stem.endswith(("аа", "ээ", "оо", "өө")):
            vowel = last_harmony_vowel(stem) or last_vowel(stem)
            wanted = "ний" if vowel in FRONT else "ны" if vowel in BACK else None
            if not wanted or wanted == wrong:
                continue
            candidate = stem + wanted + tail
            if candidate != folded:
                return candidate
            continue
        vowel = last_harmony_vowel(stem) or last_vowel(stem)
        wanted = "ийн" if vowel in FRONT else "ын" if vowel in BACK else None
        if not wanted:
            continue
        candidate = stem + wanted + tail
        if candidate != folded and (
            dictionary.contains(candidate) or dictionary.in_wordlist(candidate)
        ):
            return candidate
    return None


def suggest_negative_gui(word: str, dictionary: DictionaryProvider) -> str | None:
    """Negation is -гүй (ү), not -гуй."""
    folded = word.casefold()
    if not folded.endswith("гуй") or len(folded) < 6:
        return None
    candidate = folded[:-3] + "гүй"
    if dictionary.contains(candidate):
        return candidate
    return None


_VOWELS = "аэиоуөүяёеюы"

_I_DROP_GROUPS: tuple[tuple[tuple[str, ...], dict[str, str]], ...] = (
    (("өөс", "оос", "ээс", "аас"), _ABLATIVE),
    (("өөр", "оор", "ээр", "аар"), _INSTRUMENTAL),
    (("ийн", "ын"), _GENITIVE),
    (("ийг", "ыг"), _ACCUSATIVE),
    (("өө", "оо", "ээ", "аа"), _REFLEXIVE),
)


def suggest_i_drop(word: str, dictionary: DictionaryProvider) -> str | None:
    """Last-syllable и drops before a vowel-initial suffix if the stem is a known word."""
    folded = word.casefold()
    for wrong, right in (("иноо", "ноо"), ("инээ", "нээ"), ("инөө", "нөө"), ("инаа", "наа")):
        if not folded.endswith(wrong) or len(folded) < len(wrong) + 2:
            continue
        candidate = folded[: -len(wrong)] + right
        if dictionary.contains(candidate) or dictionary.in_wordlist(candidate):
            return candidate
    for group, mapping in _I_DROP_GROUPS:
        matched = next(
            (suffix for suffix in sorted(group, key=len, reverse=True) if folded.endswith(suffix)),
            None,
        )
        if matched is None or len(folded) - len(matched) < 3:
            continue
        stem = folded[: -len(matched)]
        if not stem[-1:].isalpha() or stem[-1] in _VOWELS:
            continue
        i_at = stem.rfind("и")
        if i_at != len(stem) - 2:
            continue
        if any(ch in _VOWELS for ch in stem[i_at + 1 :]):
            continue
        if not any(ch in _VOWELS for ch in stem[:i_at]):
            continue
        if not (dictionary.contains(stem) or dictionary.in_wordlist(stem)):
            continue
        dropped = stem[:i_at] + stem[i_at + 1 :]
        if not dropped or dropped[-1] in _VOWELS:
            continue
        if dropped[-1] in "гжшч" and mapping in (_GENITIVE, _ACCUSATIVE):
            wanted = "ийн" if mapping is _GENITIVE else "ийг"
        else:
            wanted = mapping.get(last_harmony_vowel(dropped) or last_vowel(dropped) or "") or matched
        candidate = dropped + wanted
        if candidate != folded:
            return candidate
    return None


# -лах/-лэх verbs: before -даг/-сан/-ж/-на the connecting vowel and л may swap or drop.
# туслах → тусалдаг (not тусладаг); дуулах → дуулдаг; хайрлах → хайрладаг (kept).
_LAH_VERBS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("лах", "а", ("даг", "сан", "вал", "на", "ж")),
    ("лэх", "э", ("дэг", "сэн", "вэл", "нэ", "ж")),
    ("лох", "о", ("дог", "сон", "вол", "но", "ж")),
    ("лөх", "ө", ("дөг", "сөн", "вөл", "нө", "ж")),
)
_KEEP_LAH_STEM = frozenset("лрв")
_DROP_LAH_STEM = frozenset("аэиоуөү")


def _pick_lah_form(
    stem: str,
    swapped: str,
    dropped: str,
    swapped_ok: bool,
    dropped_ok: bool,
) -> str | None:
    prefer_drop = stem[-1:] in _DROP_LAH_STEM
    if swapped_ok and dropped_ok:
        return dropped if prefer_drop else swapped
    if swapped_ok:
        return swapped
    if dropped_ok:
        return dropped
    if stem[-1:] in _KEEP_LAH_STEM:
        return None
    return dropped if prefer_drop else swapped


def _lah_correct_form(folded: str, dictionary: DictionaryProvider) -> str | None:
    """School form of a -лах verb plus -даг/-сан/-ж/-на, or the word itself if already right."""
    for lax, vowel, suffixes in _LAH_VERBS:
        connector = "л" + vowel
        for suffix in suffixes:
            if not folded.endswith(suffix) or len(folded) < len(suffix) + len(connector) + 2:
                continue
            body = folded[: -len(suffix)]
            if not body.endswith(connector):
                continue
            stem = body[: -len(connector)]
            if len(stem) < 2:
                continue
            if not _known_stem(stem + lax, dictionary):
                continue
            if stem[-1:] in _KEEP_LAH_STEM:
                return folded
            swapped = stem + vowel + "л" + suffix
            dropped = stem + "л" + suffix
            chosen = _pick_lah_form(
                stem,
                swapped,
                dropped,
                _known_stem(swapped, dictionary),
                _known_stem(dropped, dictionary),
            )
            return chosen or folded
    return None


def suggest_lah_verb(word: str, dictionary: DictionaryProvider) -> str | None:
    """тусладаг → тусалдаг, эхлэдэг → эхэлдэг, дууладаг → дуулдаг."""
    folded = word.casefold()
    correct = _lah_correct_form(folded, dictionary)
    if correct and correct != folded:
        return correct
    return None


_X_CONNECT_VOWELS = "аэиоуөү"
_X_SUFFIX_GROUPS: tuple[tuple[tuple[str, ...], dict[str, str] | None], ...] = (
    (("хөөр", "хоор", "хээр", "хаар"), _INSTRUMENTAL),
    (("хөөс", "хоос", "хээс", "хаас"), _ABLATIVE),
    (("хөд", "ход", "хэд", "хад"), _VERBAL_DATIVE),
    (("хгүй",), None),
)


_X_REFLEXIVE = {
    "а": "хдаа",
    "я": "хдаа",
    "у": "хдаа",
    "ы": "хдаа",
    "э": "хдээ",
    "е": "хдээ",
    "и": "хдээ",
    "о": "хдоо",
    "ё": "хдоо",
    "ө": "хдөө",
    "ү": "хдөө",
}


def suggest_vowel_before_x(word: str, dictionary: DictionaryProvider) -> str | None:
    """Verb х is written after a vowel: байгуулхаар → байгуулахаар."""
    folded = word.casefold()
    matched = next(
        (
            tail
            for tail in ("хдөө", "хдоо", "хдээ", "хдаа")
            if folded.endswith(tail) and len(folded) - len(tail) >= 2
        ),
        None,
    )
    if matched:
        before = folded[: -len(matched)]
        if before[-1:] not in _VOWELS and before[-1:].isalpha():
            found: list[str] = []
            for vowel in _X_CONNECT_VOWELS:
                infinitive = before + vowel + "х"
                if not _known_stem(infinitive, dictionary):
                    continue
                wanted = _X_REFLEXIVE.get(last_vowel(infinitive) or "")
                if not wanted:
                    continue
                candidate = before + vowel + wanted
                if candidate != folded:
                    found.append(candidate)
            if found:
                known = [item for item in found if dictionary.contains(item)]
                return (known or found)[0]
    for tails, mapping in _X_SUFFIX_GROUPS:
        matched = next(
            (tail for tail in sorted(tails, key=len, reverse=True) if folded.endswith(tail)),
            None,
        )
        if matched is None or len(folded) - len(matched) < 2:
            continue
        before = folded[: -len(matched)]
        if before[-1:] in _VOWELS or not before[-1:].isalpha():
            continue
        found: list[str] = []
        for vowel in _X_CONNECT_VOWELS:
            infinitive = before + vowel + "х"
            if not _known_stem(infinitive, dictionary):
                continue
            if mapping is None:
                candidate = before + vowel + matched
            else:
                ending = mapping.get(last_vowel(infinitive) or "")
                if not ending:
                    continue
                candidate = infinitive + ending
            if candidate != folded:
                found.append(candidate)
        if not found:
            continue
        known = [item for item in found if dictionary.contains(item)]
        return (known or found)[0]
    return None


def _allowed_x_reflexive(infinitive: str) -> set[str]:
    """-хдаа/-хдээ/-хдоо/-хдөө follows the last vowel of the infinitive."""
    wanted = _X_REFLEXIVE.get(last_vowel(infinitive) or "")
    return {wanted} if wanted else set()


def _kept_x_reflexive(folded: str, dictionary: DictionaryProvider) -> bool:
    matched = next(
        (
            tail
            for tail in ("хдөө", "хдоо", "хдээ", "хдаа")
            if folded.endswith(tail) and len(folded) > len(tail) + 1
        ),
        None,
    )
    if matched is None:
        return False
    infinitive = folded[: -len(matched)] + "х"
    return _known_stem(infinitive, dictionary) and matched in _allowed_x_reflexive(infinitive)


def suggest_x_reflexive(word: str, dictionary: DictionaryProvider) -> str | None:
    """When-doing -хдаа/-хдээ/-хдоо/-хдөө follows the infinitive vowel."""
    folded = word.casefold()
    matched = next(
        (
            tail
            for tail in ("хдөө", "хдоо", "хдээ", "хдаа")
            if folded.endswith(tail) and len(folded) > len(tail) + 1
        ),
        None,
    )
    if matched is None:
        return None
    stem = folded[: -len(matched)]
    infinitive = stem + "х"
    if not _known_stem(infinitive, dictionary):
        return None
    if matched in _allowed_x_reflexive(infinitive):
        return None
    wanted = _X_REFLEXIVE.get(last_vowel(infinitive) or "")
    if not wanted or wanted == matched:
        return None
    return stem + wanted


_PLURAL_TAILS = (
    "ийг",
    "ыг",
    "ийн",
    "ын",
    "аас",
    "ээс",
    "оос",
    "өөс",
    "тай",
    "тэй",
    "той",
    "хээ",
    "хаа",
    "хоо",
    "хөө",
    "нд",
)

_AGENT_PLURAL = (
    ("тэнгүүд", "тнүүд"),
    ("тангууд", "тнууд"),
    ("тонгүүд", "тнууд"),
    ("төнгүүд", "тнүүд"),
    ("тэнгууд", "тнүүд"),
    ("тангүүд", "тнууд"),
    ("тонгууд", "тнууд"),
    ("төнгууд", "тнүүд"),
    ("тнгүүд", "тнүүд"),
    ("тнгууд", "тнууд"),
    ("тэнүүд", "тнүүд"),
    ("танууд", "тнууд"),
    ("тонууд", "тнууд"),
    ("төнүүд", "тнүүд"),
)


def _split_plural_tail(folded: str) -> tuple[str, str]:
    core = folded
    tail = ""
    for _ in range(2):
        matched = next(
            (
                item
                for item in sorted(_PLURAL_TAILS, key=len, reverse=True)
                if core.endswith(item) and len(core) - len(item) >= 4
            ),
            None,
        )
        if matched is None:
            break
        tail = matched + tail
        core = core[: -len(matched)]
    return core, tail


def suggest_n_plural(word: str, dictionary: DictionaryProvider) -> str | None:
    """-тан/-тэн nouns drop the last vowel in the plural (ажилтангууд → ажилтнууд)."""
    folded = word.casefold()
    core, tail = _split_plural_tail(folded)
    for wrong, right in _AGENT_PLURAL:
        if not core.endswith(wrong) or len(core) < len(wrong) + 2:
            continue
        noun = core[: -len(wrong)] + wrong[:3]
        candidate = core[: -len(wrong)] + right + tail
        if candidate == folded:
            continue
        if _known_stem(noun, dictionary) or _known_stem(candidate, dictionary) or dictionary.contains(
            core[: -len(wrong)] + right
        ):
            return candidate
    return None


def suggest_n_plural_g(word: str, dictionary: DictionaryProvider) -> str | None:
    """Other н-stems take -гууд/-гүүд (дүнүүд → дүнгүүд)."""
    folded = word.casefold()
    core, tail = _split_plural_tail(folded)
    if core.endswith("үүд"):
        suffix = "үүд"
    elif core.endswith("ууд"):
        suffix = "ууд"
    else:
        return None
    stem = core[: -len(suffix)]
    if not stem.endswith("н") or stem.endswith(("тан", "тэн", "тон", "төн", "тн")):
        return None
    candidate = stem + "г" + suffix
    if candidate == core:
        return None
    if dictionary.contains(candidate) or dictionary.in_wordlist(candidate):
        return candidate + tail
    return None


def suggest_plural_harmony(word: str, dictionary: DictionaryProvider) -> str | None:
    """Plural -ууд/-үүд follows the last stem vowel."""
    folded = word.casefold()
    if folded.endswith("үүд"):
        matched, other = "үүд", "ууд"
    elif folded.endswith("ууд"):
        matched, other = "ууд", "үүд"
    else:
        return None
    if len(folded) < 6:
        return None
    stem = folded[: -len(matched)]
    vowel = last_vowel(stem)
    wanted = "үүд" if vowel in FRONT else "ууд" if vowel in BACK else None
    if not wanted or wanted == matched:
        return None
    candidate = stem + wanted
    if dictionary.contains(candidate):
        return candidate
    return None


def suggest_drop_soft_sign(word: str, dictionary: DictionaryProvider) -> str | None:
    """Drop ь when the dictionary form is written without it (дурьдах → дурдах)."""
    folded = word.casefold()
    if "ь" not in folded or len(folded) < 5:
        return None
    start = 0
    while True:
        idx = folded.find("ь", start)
        if idx < 0:
            break
        candidate = folded[:idx] + folded[idx + 1 :]
        if len(candidate) >= 4 and (
            dictionary.contains(candidate) or dictionary.in_wordlist(candidate)
        ):
            return candidate
        start = idx + 1
    return _suggest_moved_soft_sign(folded, dictionary)


def _suggest_moved_soft_sign(folded: str, dictionary: DictionaryProvider) -> str | None:
    """комьпютер → компьютер: ь sits next to the wrong letter."""
    idx = folded.find("ь")
    while idx >= 0:
        if idx + 1 < len(folded):
            swapped = folded[:idx] + folded[idx + 1] + "ь" + folded[idx + 2 :]
            if swapped != folded and (
                dictionary.contains(swapped) or dictionary.in_wordlist(swapped)
            ):
                return swapped
        if idx > 0:
            swapped = folded[: idx - 1] + "ь" + folded[idx - 1] + folded[idx + 1 :]
            if swapped != folded and (
                dictionary.contains(swapped) or dictionary.in_wordlist(swapped)
            ):
                return swapped
        idx = folded.find("ь", idx + 1)
    return None


def suggest_soft_sign_dative(word: str, dictionary: DictionaryProvider) -> str | None:
    """After ь the dative is -д, not -т (сургуульт → сургуульд)."""
    folded = word.casefold()
    if not folded.endswith("ьт") or len(folded) < 5:
        return None
    candidate = folded[:-1] + "д"
    if dictionary.contains(candidate):
        return candidate
    return None


def suggest_soft_sign_genitive(word: str, dictionary: DictionaryProvider) -> str | None:
    """After ь the genitive/accusative is -ийн/-ийг (сургуульын → сургуулийн)."""
    folded = word.casefold()
    for wrong, right in (("ьын", "ийн"), ("ьыг", "ийг")):
        if not folded.endswith(wrong) or len(folded) < 5:
            continue
        candidate = folded[: -len(wrong)] + right
        if dictionary.contains(candidate):
            return candidate
    return None
