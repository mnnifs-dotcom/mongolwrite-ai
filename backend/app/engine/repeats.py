from __future__ import annotations

import uuid

from app.engine.models import Category, Correction, Severity, Source
from app.engine.text import Token


def check_repeated_words(tokens: list[Token], text: str) -> list[Correction]:
    corrections: list[Correction] = []
    for prev, curr in zip(tokens, tokens[1:], strict=False):
        if prev.text.casefold() != curr.text.casefold():
            continue
        gap = text[prev.end : curr.start]
        if not gap or not gap.isspace():
            continue
        corrections.append(
            Correction(
                id=str(uuid.uuid4()),
                category=Category.REDUNDANCY,
                original_text=f"{prev.text} {curr.text}",
                suggested_text=curr.text,
                explanation="Ижил үг дараалан давтагдсан байна.",
                confidence=0.92,
                start=prev.start,
                end=curr.end,
                source=Source.RULE,
                rule_id="repeated_word",
                severity=Severity.WARNING,
            )
        )
    return corrections
