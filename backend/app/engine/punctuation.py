from __future__ import annotations

import re
import uuid

from app.engine.models import Category, Correction, Severity, Source
from app.engine.text import Token

_MULTI_SPACE = re.compile(r"[^\S\n]{2,}")
_SPACE_BEFORE_PUNCT = re.compile(r" +([,.;:!?])")
_MISSING_SPACE_AFTER_COMMA = re.compile(r",(?=\S)")
_REPEAT_PUNCT = re.compile(r"([!?])\1+")
_REPEAT_DOTS = re.compile(r"\.{4,}")
_REPEAT_COMMA = re.compile(r",{2,}")
_JUNK_COMMA_CHUNK = re.compile(r",(?:ан|эн),")

_CONVERBS_NEEDING_COMMA = frozenset(
    {
        "авч",
        "үзэж",
        "хийж",
        "уншиж",
        "шалгаж",
        "сонсож",
        "танилцан",
        "танилцаж",
        "илгээж",
        "хүргүүлж",
    }
)
_NO_COMMA_AFTER = frozenset(
    {
        "уу",
        "үү",
        "юу",
        "бэ",
        "вэ",
        "ч",
        "л",
        "нь",
        "гэж",
        "байна",
        "болно",
        "байх",
        "ажиллана",
        "ажиллах",
        "болон",
        "буюу",
    }
)


def check_punctuation(text: str) -> list[Correction]:
    corrections: list[Correction] = []

    for match in _MULTI_SPACE.finditer(text):
        corrections.append(
            _punct(
                match.group(0),
                " ",
                "Илүү зай байна.",
                "extra_whitespace",
                match.start(),
                match.end(),
                Severity.WARNING,
                0.95,
            )
        )

    for match in _SPACE_BEFORE_PUNCT.finditer(text):
        corrections.append(
            _punct(
                match.group(0),
                match.group(1),
                "Цэг, таслалын өмнө зай байх ёсгүй.",
                "space_before_punct",
                match.start(),
                match.end(),
                Severity.ERROR,
                0.93,
            )
        )

    for match in _JUNK_COMMA_CHUNK.finditer(text):
        corrections.append(
            _punct(
                match.group(0),
                ",",
                "Таслалын ард илүүц үсэг орсон байна.",
                "junk_comma_fragment",
                match.start(),
                match.end(),
                Severity.ERROR,
                0.94,
            )
        )

    for match in _MISSING_SPACE_AFTER_COMMA.finditer(text):
        nxt = text[match.end() : match.end() + 1]
        if nxt.isdigit() or nxt in ",.;:!?":
            continue
        corrections.append(
            _punct(
                match.group(0),
                ", ",
                "Таслалын дараа зай дутуу байна.",
                "missing_space_after_comma",
                match.start(),
                match.end(),
                Severity.ERROR,
                0.9,
            )
        )

    for match in _REPEAT_PUNCT.finditer(text):
        corrections.append(
            _punct(
                match.group(0),
                match.group(1),
                "Давхардсан тэмдэгтийг нэг болгоно.",
                "repeated_punctuation",
                match.start(),
                match.end(),
                Severity.WARNING,
                0.88,
            )
        )

    for match in _REPEAT_COMMA.finditer(text):
        corrections.append(
            _punct(
                match.group(0),
                ",",
                "Давхардсан таслалыг нэг болгоно.",
                "repeated_comma",
                match.start(),
                match.end(),
                Severity.WARNING,
                0.9,
            )
        )

    for match in _REPEAT_DOTS.finditer(text):
        corrections.append(
            _punct(
                match.group(0),
                "…",
                "Олон цэгийг нэг эллипсис болгоно.",
                "repeated_dots",
                match.start(),
                match.end(),
                Severity.SUGGESTION,
                0.8,
            )
        )

    return corrections


def check_missing_comma_after_converb(tokens: list[Token], text: str) -> list[Correction]:
    corrections: list[Correction] = []
    for prev, curr in zip(tokens, tokens[1:], strict=False):
        if prev.text.casefold() not in _CONVERBS_NEEDING_COMMA:
            continue
        if curr.text.casefold() in _NO_COMMA_AFTER or len(curr.text) < 4:
            continue
        gap = text[prev.end : curr.start]
        if not gap or "," in gap:
            continue
        if not gap.isspace():
            continue
        corrections.append(
            _punct(
                prev.text,
                f"{prev.text},",
                "Хоёр үйл үгийн хооронд таслал дутуу байна.",
                "missing_comma_after_converb",
                prev.start,
                prev.end,
                Severity.ERROR,
                0.84,
            )
        )
    return corrections


def _punct(
    original: str,
    suggested: str,
    explanation: str,
    rule_id: str,
    start: int,
    end: int,
    severity: Severity,
    confidence: float,
) -> Correction:
    return Correction(
        id=str(uuid.uuid4()),
        category=Category.PUNCTUATION,
        original_text=original,
        suggested_text=suggested,
        explanation=explanation,
        confidence=confidence,
        start=start,
        end=end,
        source=Source.RULE,
        rule_id=rule_id,
        severity=severity,
    )
