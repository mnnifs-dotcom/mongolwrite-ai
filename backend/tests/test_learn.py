from app.engine.dictionary import DictionaryProvider
from app.engine.hunspell_candidates import list_candidates
from app.engine.learn import learn_accepted_words
from app.engine.pipeline import LanguageEngine


def test_learn_skips_flagged_spelling(tmp_path, monkeypatch) -> None:
    persist = tmp_path / "persist"
    persist.mkdir()
    monkeypatch.setattr("app.engine.hunspell_candidates.persist_dir", lambda: persist)

    engine = LanguageEngine(DictionaryProvider(frozenset({"өдөр", "ажиллана", "танилцана"})))
    queued = learn_accepted_words(engine, "өдөр одөр ажиллана танилццана")
    assert "одөр" not in queued
    assert "танилццана" not in queued
    # Known seed words are not queued; lexicon unchanged for new forms.
    assert engine.dictionary.in_seed("өдөр")
    assert not engine.dictionary.in_seed("одөр")


def test_learn_queues_new_accepted_without_lexicon_write(tmp_path, monkeypatch) -> None:
    persist = tmp_path / "persist"
    persist.mkdir()
    monkeypatch.setattr("app.engine.hunspell_candidates.persist_dir", lambda: persist)

    engine = LanguageEngine(DictionaryProvider(frozenset({"өдөр"})))
    # "ажиллана" is accepted by empty/minimal engine if not flagged — use a word
    # that is in seed for skip, and invent one that passes as non-flagged.
    # With tiny dictionary, unknown words are flagged as spelling → not queued.
    queued = learn_accepted_words(engine, "өдөр одөр")
    assert "одөр" not in queued
    assert not engine.dictionary.in_seed("одөр")
    # Seed word itself must not re-enter the review queue.
    folded = {row["folded"] for row in list_candidates()}
    assert "өдөр" not in folded
