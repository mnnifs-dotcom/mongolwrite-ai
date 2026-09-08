from app.engine.dictionary import DictionaryProvider
from app.engine.frequency import load_frequency
from app.engine.pipeline import LanguageEngine


def test_frequency_ranks_common_insert() -> None:
    local = LanguageEngine(
        DictionaryProvider(
            frozenset({"технологи", "технолга"}),
            frequency={"технологи": 8000, "технолга": 4},
        )
    )
    found = local.check("технолги")
    item = next(row for row in found if row.original_text == "технолги")
    assert item.suggested_text == "технологи"


def test_frequency_ranks_common_over_rare_same_distance() -> None:
    dictionary = DictionaryProvider(
        frozenset({"байгууллага", "байгуулаг"}),
        frequency={"байгууллага": 9000, "байгуулаг": 5},
    )
    options = dictionary.suggest_many("байгууллаг", limit=4)
    assert options[0] == "байгууллага"


def test_frequent_stem_keeps_case_form() -> None:
    local = LanguageEngine(
        DictionaryProvider(
            frozenset({"аав"}),
            frequency={"вэбсайт": 200, "оффис": 80},
        )
    )
    for word in ("вэбсайт", "вэбсайтад", "оффис", "оффисын"):
        assert not any(item.original_text == word for item in local.check(word)), word


def test_load_frequency_ignores_comments(tmp_path) -> None:
    path = tmp_path / "freq.txt"
    path.write_text("# comment\nсургууль\t120\n\nажил 7\n", encoding="utf-8")
    counts = load_frequency(path)
    assert counts["сургууль"] == 120
    assert counts["ажил"] == 7
