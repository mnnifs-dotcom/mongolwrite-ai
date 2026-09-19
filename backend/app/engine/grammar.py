from __future__ import annotations

import re
import uuid
from collections.abc import Callable, Collection

from app.engine.dictionary import DictionaryProvider
from app.engine.harmony import last_vowel, question_particle, ve_particle
from app.engine.models import Category, Correction, Severity, Source
from app.engine.text import Token

_QUESTION = frozenset({"уу", "үү"})
_VE = frozenset({"бэ", "вэ"})
_GLUED_QUESTION = re.compile(r"^(.+?)(уу|үү)$", re.IGNORECASE)
_GLUED_AUX = re.compile(
    r"^(.+[жч])(байна|байгаа|байсан|байх|байдаг|байлаа|байжээ|болно|болох)$",
    re.IGNORECASE,
)
_GLUED_DIRECTION = re.compile(r"^(.+)(руу|рүү)$", re.IGNORECASE)
_FINITE_ENDINGS = (
    "на",
    "нэ",
    "но",
    "нө",
    "лаа",
    "лээ",
    "лоо",
    "лөө",
    "сан",
    "сэн",
    "сон",
    "сөн",
    "жээ",
    "чээ",
)
_BACK = frozenset("аоуяёы")
_FRONT = frozenset("эөүеи")


def check_grammar(
    tokens: list[Token],
    text: str,
    dictionary: DictionaryProvider,
) -> list[Correction]:
    corrections: list[Correction] = []
    corrections.extend(
        _particle_harmony(
            tokens, text, _QUESTION, question_particle, "уу/үү", "question_particle_harmony"
        )
    )
    corrections.extend(
        _particle_harmony(tokens, text, _VE, ve_particle, "бэ/вэ", "ve_particle_harmony")
    )
    corrections.extend(
        _particle_harmony(
            tokens, text, {"руу", "рүү"}, _directive, "руу/рүү", "directive_harmony"
        )
    )
    corrections.extend(_glued_forms(tokens, dictionary))
    return corrections


def _directive(word: str) -> str | None:
    vowel = last_vowel(word)
    if vowel in _FRONT:
        return "рүү"
    if vowel in _BACK:
        return "руу"
    return None


def _particle_harmony(
    tokens: list[Token],
    text: str,
    particles: Collection[str],
    wanted_fn: Callable[[str], str | None],
    label: str,
    rule_id: str,
) -> list[Correction]:
    corrections: list[Correction] = []
    for prev, curr in zip(tokens, tokens[1:], strict=False):
        folded = curr.text.casefold()
        if folded not in particles:
            continue
        if not text[prev.end : curr.start].isspace():
            continue
        wanted = wanted_fn(prev.text)
        if not wanted or wanted == folded:
            continue
        replacement = wanted
        if curr.text[:1].isupper():
            replacement = wanted[:1].upper() + wanted[1:]
        corrections.append(
            Correction(
                id=str(uuid.uuid4()),
                category=Category.GRAMMAR,
                original_text=curr.text,
                suggested_text=replacement,
                explanation=f"«{label}» нь өмнөх үгийн эгшгийн эв нэгдлийг дагана.",
                confidence=0.9,
                start=curr.start,
                end=curr.end,
                source=Source.RULE,
                rule_id=rule_id,
                severity=Severity.ERROR,
            )
        )
    return corrections


def _glued_forms(tokens: list[Token], dictionary: DictionaryProvider) -> list[Correction]:
    corrections: list[Correction] = []
    for token in tokens:
        folded = token.text.casefold()
        aux = _GLUED_AUX.match(folded)
        if aux:
            corrections.append(
                _glued(
                    token,
                    f"{_keep_case(token.text, aux.group(1))} {aux.group(2)}",
                    "Туслах үйл үг «байна/болно»-г тусад нь бичнэ.",
                    "glued_auxiliary",
                )
            )
            continue
        question = _GLUED_QUESTION.match(folded)
        if question and _looks_like_finite_verb(question.group(1)):
            particle = question_particle(question.group(1)) or question.group(2).casefold()
            corrections.append(
                _glued(
                    token,
                    f"{_keep_case(token.text, question.group(1))} {particle}",
                    "Асуух «уу/үү»-г тусад нь бичнэ.",
                    "glued_question_particle",
                )
            )
            continue
        direction = _GLUED_DIRECTION.match(folded)
        stem = direction.group(1) if direction else ""
        if direction and len(stem) >= 3 and dictionary.contains(stem):
            particle = _directive(stem) or direction.group(2).casefold()
            corrections.append(
                _glued(
                    token,
                    f"{_keep_case(token.text, stem)} {particle}",
                    "Чиглэлийн «руу/рүү»-г тусад нь бичнэ.",
                    "glued_directive",
                )
            )
            continue
        if dictionary.contains(folded):
            continue
        particle = _suggest_separate_particle(folded, dictionary)
        if particle:
            corrections.append(
                _glued(
                    token,
                    _keep_case(token.text, particle),
                    "Энэ нөхцөл, өгүүлэхүүнийг тусад нь бичнэ.",
                    "separate_particle",
                )
            )
            continue
        split = _suggest_glued_split(folded, dictionary)
        if split:
            corrections.append(
                _glued(
                    token,
                    _keep_case(token.text, split),
                    "Хоёр үг наалдсан байна. Зай эсвэл таслал дутуу.",
                    "glued_words",
                )
            )
    return corrections


_CONVERB_LEFT = frozenset(
    {"авч", "үзэж", "хийж", "уншиж", "шалгаж", "сонсож", "танилцан", "танилцаж"}
)


_SEPARATE_TAILS = ("шүү", "нь")
_CH_HOSTS = frozenset({"ямар", "хэдий", "гэсэн", "хэзээ", "хэнд", "юу"})
_L_HOSTS = frozenset({"гэж", "сайн", "тийм", "ийм"})
_DAA_HOSTS = frozenset({"байна", "болно", "тийм", "ийм", "сайн"})


def _suggest_separate_particle(word: str, dictionary: DictionaryProvider) -> str | None:
    if dictionary.contains(word):
        return None
    if word.endswith("ч") and word[:-1] in _CH_HOSTS:
        return f"{word[:-1]} ч"
    if word.endswith("л") and word[:-1] in _L_HOSTS:
        return f"{word[:-1]} л"
    if word.endswith("даа") and word[:-3] in _DAA_HOSTS:
        return f"{word[:-3]} даа"
    for tail in _SEPARATE_TAILS:
        if not word.endswith(tail) or len(word) < len(tail) + 3:
            continue
        stem = word[: -len(tail)]
        if dictionary.in_wordlist(stem) or dictionary.contains(stem):
            return f"{stem} {tail}"
    return None


def _suggest_glued_split(word: str, dictionary: DictionaryProvider) -> str | None:
    if len(word) < 7:
        return None
    hits: list[str] = []
    for i in range(3, len(word) - 3):
        left, right = word[:i], word[i:]
        if left in _CONVERB_LEFT and dictionary.contains(right):
            hits.append(f"{left}, {right}")
            continue
        if len(left) < 4 or len(right) < 4:
            continue
        if dictionary.in_wordlist(left) and dictionary.in_wordlist(right):
            hits.append(f"{left} {right}")
    unique = list(dict.fromkeys(hits))
    preferred = [item for item in unique if ", " in item]
    if len(preferred) == 1:
        return preferred[0]
    if len(unique) == 1:
        return unique[0]
    return None


def _glued(token: Token, suggested: str, explanation: str, rule_id: str) -> Correction:
    return Correction(
        id=str(uuid.uuid4()),
        category=Category.GRAMMAR,
        original_text=token.text,
        suggested_text=suggested,
        explanation=explanation,
        confidence=0.9,
        start=token.start,
        end=token.end,
        source=Source.RULE,
        rule_id=rule_id,
        severity=Severity.ERROR,
    )


def _looks_like_finite_verb(stem: str) -> bool:
    return len(stem) >= 4 and stem.endswith(_FINITE_ENDINGS)


def _keep_case(original: str, stem: str) -> str:
    if original[:1].isupper():
        return stem[:1].upper() + stem[1:]
    return stem
