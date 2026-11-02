from __future__ import annotations

from app.engine.admin_review import parse_word_list, preview_keep_drop


class _FakeDict:
    def __init__(self, seeded: set[str]):
        self._seeded = {w.casefold() for w in seeded}

    def in_seed(self, word: str) -> bool:
        return word.casefold() in self._seeded

    def contains(self, word: str) -> bool:
        return word.casefold() in self._seeded


def test_parse_word_list_unique() -> None:
    words = parse_word_list("сайн\nбайна\nсайн\nморь\n")
    assert words == ["сайн", "байна", "морь"]


def test_preview_keep_drop_splits_lexicon_vs_queue() -> None:
    batch = ["алтан", "мөнгөн", "зэс", "төмөр"]
    approved = "алтан\nмөнгөн\n"
    preview = preview_keep_drop(
        batch_words=batch,
        approved_text=approved,
        dictionary=_FakeDict({"алтан", "зэс"}),
    )
    assert preview["keep"] == ["алтан", "мөнгөн"]
    assert "зэс" in preview["remove_from_lexicon"]
    assert "төмөр" in preview["do_not_add"]
    assert preview["drop_count"] == 2
