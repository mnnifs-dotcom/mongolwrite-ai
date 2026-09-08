from __future__ import annotations

from app.engine.models import Correction


def rank_corrections(corrections: list[Correction]) -> list[Correction]:
    """Drop overlapping lower-confidence hits; keep document order."""
    ordered = sorted(corrections, key=lambda c: (c.start, -c.confidence, c.end))
    kept: list[Correction] = []
    for item in ordered:
        if any(not (item.end <= prev.start or item.start >= prev.end) for prev in kept):
            continue
        kept.append(item)
    return sorted(kept, key=lambda c: c.start)
