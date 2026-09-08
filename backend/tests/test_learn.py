from app.engine.dictionary import DictionaryProvider
from app.engine.learn import learn_accepted_words
from app.engine.pipeline import LanguageEngine


def test_learn_skips_flagged_spelling() -> None:
    engine = LanguageEngine(DictionaryProvider(frozenset({"өдөр", "ажиллана", "танилцана"})))
    added = learn_accepted_words(engine, "өдөр одөр ажиллана танилццана")
    assert "одөр" not in added
    assert "танилццана" not in added
    assert engine.dictionary.contains("өдөр")
    assert engine.dictionary.contains("ажиллана")


def test_learn_skips_unknown_words() -> None:
    engine = LanguageEngine(DictionaryProvider(frozenset({"өдөр"})))
    added = learn_accepted_words(engine, "өдөр одөр")
    assert "одөр" not in added
