from __future__ import annotations

from app.engine.dictionary import DictionaryProvider


def test_list_lexicon_letter_and_search() -> None:
    dictionary = DictionaryProvider(
        frozenset({"ажил", "амьдрал", "барилга", "бүтээл", "засаг"}),
        use_hunspell=False,
        frequency={},
    )
    page = dictionary.list_lexicon(letter="а", offset=0, limit=50)
    assert page["total"] == 2
    assert page["words"] == ["ажил", "амьдрал"]
    found = dictionary.list_lexicon(query="рил", offset=0, limit=50)
    assert found["words"] == ["барилга"]
    assert dictionary.curated_lemmas() == ["ажил", "амьдрал", "барилга", "бүтээл", "засаг"]


def test_remove_words_blocks_contains(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.engine.dictionary.persist_dir", lambda: tmp_path)
    monkeypatch.setattr(
        "app.engine.dictionary.user_dictionary_path",
        lambda: tmp_path / "user_dictionary.txt",
    )
    monkeypatch.setattr(
        "app.engine.dictionary.removed_lexicon_path",
        lambda: tmp_path / "lexicon_removed.json",
    )
    dictionary = DictionaryProvider(
        frozenset({"тестовог", "хадгал"}),
        use_hunspell=False,
        frequency={},
    )
    dictionary._persist_user = True
    assert dictionary.contains("тестовог")
    removed = dictionary.remove_words(["тестовог"])
    assert removed == ["тестовог"]
    assert not dictionary.contains("тестовог")
    assert not dictionary.in_seed("тестовог")
    listing = dictionary.list_lexicon(query="тест", offset=0, limit=20)
    assert listing["total"] == 0


def test_remove_single_letter_lemma(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.engine.dictionary.persist_dir", lambda: tmp_path)
    monkeypatch.setattr(
        "app.engine.dictionary.user_dictionary_path",
        lambda: tmp_path / "user_dictionary.txt",
    )
    monkeypatch.setattr(
        "app.engine.dictionary.removed_lexicon_path",
        lambda: tmp_path / "lexicon_removed.json",
    )
    dictionary = DictionaryProvider(
        frozenset({"а", "аав", "барилга"}),
        use_hunspell=False,
        frequency={},
    )
    dictionary._persist_user = True
    assert dictionary.contains("а")
    removed = dictionary.remove_words(["а"])
    assert removed == ["а"]
    assert not dictionary.contains("а")
    assert "а" not in dictionary.list_lexicon(letter="а", offset=0, limit=50)["words"]
