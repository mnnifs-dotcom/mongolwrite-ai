from __future__ import annotations

from app.engine.lexicon_audit import audit_curated_lexicon
from app.engine.pipeline import LanguageEngine


def test_audit_flags_rule_first_lemma(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.engine.dictionary.persist_dir", lambda: tmp_path)
    engine = LanguageEngine()
    # Spoken -чих- form that the checker rewrites; must surface in audit.
    engine.dictionary.ensure_curated(["ялчихаад", "ажил"])
    result = audit_curated_lexicon(engine, letter="я")
    words = {item["word"] for item in result["items"]}
    assert "ялчихаад" in words
    hit = next(item for item in result["items"] if item["word"] == "ялчихаад")
    assert hit["suggested"]
    assert hit["rule_id"]
    assert result["scanned"] >= 1
