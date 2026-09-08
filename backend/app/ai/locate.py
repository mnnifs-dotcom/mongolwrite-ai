from __future__ import annotations

import uuid

from app.engine.models import Category, Correction, Severity, Source

_CATEGORIES = {item.value: item for item in Category}
_SEVERITIES = {item.value: item for item in Severity}


def locate_corrections(text: str, raw: list[dict[str, object]]) -> list[Correction]:
    used: list[tuple[int, int]] = []
    found: list[Correction] = []
    for item in raw:
        original = str(item.get("original") or item.get("original_text") or "").strip()
        suggested = str(item.get("suggested") or item.get("suggested_text") or "")
        if not original or original == suggested:
            continue
        span = _next_span(text, original, used)
        if span is None:
            continue
        start, end = span
        used.append((start, end))
        category = _CATEGORIES.get(str(item.get("category") or "").upper(), Category.GRAMMAR)
        severity = _SEVERITIES.get(str(item.get("severity") or "error").lower(), Severity.ERROR)
        explanation = str(item.get("explanation") or "Өгүүлбэрийн утга, найруулгыг засав.")
        extras = item.get("alternatives") or item.get("suggestions") or []
        more = [str(row).strip() for row in extras if str(row).strip() and str(row).strip() != suggested]
        found.append(
            Correction(
                id=str(uuid.uuid4()),
                category=category,
                original_text=text[start:end],
                suggested_text=suggested,
                explanation=explanation,
                confidence=0.8 if severity == Severity.ERROR else 0.66,
                start=start,
                end=end,
                source=Source.AI,
                rule_id=f"ai_{category.value.lower()}",
                severity=severity,
                suggestions=more,
            )
        )
    return found


def _next_span(text: str, original: str, used: list[tuple[int, int]]) -> tuple[int, int] | None:
    start = 0
    while True:
        idx = text.find(original, start)
        if idx < 0:
            return None
        end = idx + len(original)
        if not any(not (end <= left or idx >= right) for left, right in used):
            return idx, end
        start = idx + 1
