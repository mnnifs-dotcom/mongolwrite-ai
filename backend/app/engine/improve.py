from __future__ import annotations

from app.engine.pipeline import LanguageEngine


def improve_text(
    engine: LanguageEngine,
    text: str,
    style: str = "government_official",
    rounds: int = 12,
) -> tuple[str, int]:
    """Apply non-overlapping deterministic fixes until the text settles."""
    applied = 0
    for _ in range(rounds):
        items = [
            item
            for item in engine.check(text, style)
            if item.rule_id != "unknown_word" and item.suggested_text != item.original_text
        ]
        if not items:
            break
        changed = False
        for item in sorted(items, key=lambda row: -row.start):
            if text[item.start : item.end] != item.original_text:
                continue
            text = f"{text[: item.start]}{item.suggested_text}{text[item.end :]}"
            applied += 1
            changed = True
        if not changed:
            break
    return text, applied
