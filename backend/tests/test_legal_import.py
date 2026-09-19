from __future__ import annotations

import json

from app.engine import legal_import
from app.engine.runtime import get_engine


def test_legal_import_preview_and_apply(tmp_path, monkeypatch) -> None:
    data = tmp_path / "data"
    data.mkdir()
    persist = tmp_path / "persist"
    persist.mkdir()
    (data / "legal_trusted.txt").write_text("хуулийнтомьёотест\n", encoding="utf-8")
    (data / "legal_doubt.json").write_text(
        json.dumps(
            {
                "items": [
                    {
                        "word": "эргэлзээтэйтестүг",
                        "folded": "эргэлзээтэйтестүг",
                        "legal_df": 120,
                        "reason": "test",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(legal_import, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(legal_import, "trusted_path", lambda: data / "legal_trusted.txt")
    monkeypatch.setattr(legal_import, "doubt_path", lambda: data / "legal_doubt.json")
    monkeypatch.setattr("app.engine.hunspell_candidates.persist_dir", lambda: persist)
    monkeypatch.setattr(
        "app.engine.dictionary.user_dictionary_path",
        lambda: persist / "user_dictionary.txt",
    )

    import app.engine.runtime as runtime

    runtime._engine = None
    engine = get_engine()

    preview = legal_import.legal_import_preview()
    assert preview["trusted_count"] == 1
    assert preview["doubt_count"] == 1
    assert "corpus" in preview

    result = legal_import.apply_legal_lexicon(engine)
    assert result["added_to_lexicon"] == 1
    assert result["queued_for_admin"] == 1
    assert engine.dictionary.in_seed("хуулийнтомьёотест")
    assert not engine.dictionary.in_seed("эргэлзээтэйтестүг")

    candidates = json.loads((persist / "hunspell_candidates.json").read_text(encoding="utf-8"))
    folded = {row["folded"] for row in candidates["words"]}
    assert "эргэлзээтэйтестүг" in folded
    assert all(row.get("tier") == "doubt" for row in candidates["words"] if row["folded"] == "эргэлзээтэйтестүг")

    again = legal_import.apply_legal_lexicon(engine)
    assert again["added_to_lexicon"] == 0
