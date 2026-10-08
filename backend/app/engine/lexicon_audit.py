"""Find curated lexicon lemmas that the spell-checker itself flags.

Admins copy the lexicon into the editor and see corrections — those lemmas
should not stay in the curated seed. This scan runs the same ``LanguageEngine.check``
path on each lemma (one word at a time) so results match paste-and-check.
"""

from __future__ import annotations

from typing import Any

from app.engine.pipeline import LanguageEngine


def audit_curated_lexicon(
    engine: LanguageEngine,
    *,
    letter: str = "",
    limit: int = 0,
) -> dict[str, Any]:
    """Return curated lemmas that produce a spelling mark when checked alone."""
    letter_key = letter.strip().casefold()[:1]
    lemmas = engine.dictionary.curated_lemmas()
    if letter_key:
        lemmas = [word for word in lemmas if word[:1] == letter_key]
    if limit > 0:
        lemmas = lemmas[: int(limit)]

    items: list[dict[str, str]] = []
    for word in lemmas:
        try:
            corrections = engine.check(word)
        except Exception:
            continue
        for hit in corrections:
            surface = (hit.original_text or "").casefold()
            if surface != word.casefold():
                continue
            # Skip marks that do not change the surface (noise).
            suggested = (hit.suggested_text or "").strip()
            if suggested and suggested.casefold() == word.casefold():
                continue
            items.append(
                {
                    "word": word,
                    "suggested": suggested,
                    "rule_id": hit.rule_id or "",
                    "explanation": (hit.explanation or "").strip(),
                }
            )
            break

    return {
        "items": items,
        "flagged": len(items),
        "scanned": len(lemmas),
        "lexicon_total": engine.dictionary.curated_lemma_count,
    }
