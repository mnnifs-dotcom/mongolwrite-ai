from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.engine.frequency import load_frequency
from app.engine.misspellings import lookup_misspelling

_SEED_FREQ_BONUS = 100
# Wikipedia counts at or above this are treated as established spellings.
_FREQ_TRUST = 50

_HUNSPELL: Any = None
_HUNSPELL_TRIED = False


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_wordlist_path() -> Path:
    return _repo_root() / "data" / "wordlist.txt"


def hunspell_base_path() -> Path:
    return _repo_root() / "data" / "hunspell" / "mn_MN"


def user_dictionary_path() -> Path:
    return _repo_root() / "data" / "user_dictionary.txt"


def load_user_dictionary(path: Path | None = None) -> set[str]:
    target = path or user_dictionary_path()
    if not target.exists():
        return set()
    words: set[str] = set()
    for line in target.read_text(encoding="utf-8").splitlines():
        word = line.strip()
        if not word or word.startswith("#"):
            continue
        words.add(word)
        words.add(word.casefold())
    return words


@lru_cache(maxsize=1)
def load_wordlist(path: Path | None = None) -> frozenset[str]:
    target = path or _default_wordlist_path()
    if not target.exists():
        return frozenset()
    words: set[str] = set()
    for line in target.read_text(encoding="utf-8").splitlines():
        word = line.strip()
        if not word or word.startswith("#"):
            continue
        words.add(word)
        words.add(word.casefold())
    return frozenset(words)


def load_hunspell() -> Any:
    global _HUNSPELL, _HUNSPELL_TRIED
    if _HUNSPELL_TRIED:
        return _HUNSPELL
    _HUNSPELL_TRIED = True
    base = hunspell_base_path()
    if not base.with_suffix(".dic").exists() or not base.with_suffix(".aff").exists():
        _HUNSPELL = None
        return None
    from spylls.hunspell import Dictionary

    _HUNSPELL = Dictionary.from_files(str(base))
    return _HUNSPELL


class DictionaryProvider:
    """Seed wordlist plus optional Hunspell (dict-mn)."""

    def __init__(
        self,
        words: frozenset[str] | None = None,
        *,
        use_hunspell: bool = True,
        frequency: dict[str, int] | None = None,
    ) -> None:
        if words is None:
            base = load_wordlist() | load_user_dictionary()
            self._persist_user = True
        else:
            base = set(words)
            self._persist_user = False
        self._seed: set[str] = {item.casefold() for item in base} | set(base)
        self._words: set[str] = set(base | expand_case_forms(base))
        self._near: dict[tuple[str, int], list[str]] = {}
        self._index_near()
        self._hunspell = load_hunspell() if (use_hunspell and words is None) else None
        self._lookup_cache: dict[str, bool] = {}
        if frequency is not None:
            self._wiki_freq = {
                key.casefold(): int(value)
                for key, value in frequency.items()
                if value > 0
            }
        elif words is None:
            self._wiki_freq = dict(load_frequency())
        else:
            self._wiki_freq = {}
        self._freq = dict(self._wiki_freq)
        for item in self._seed:
            folded = item.casefold()
            self._freq[folded] = self._freq.get(folded, 0) + _SEED_FREQ_BONUS
        self._freq_near: dict[tuple[str, int], list[str]] = {}
        self._index_freq_near()

    def add_words(self, words: Iterable[str]) -> list[str]:
        added: list[str] = []
        for raw in words:
            word = raw.strip()
            if len(word) < 2:
                continue
            folded = word.casefold()
            # Curated check: seed only. Hunspell-known forms are often absent from _words
            # but must still enter the user dictionary when an admin approves them.
            if folded in self._seed:
                continue
            batch = {word, folded} | expand_case_forms({folded})
            self._seed.update({word, folded})
            self._words.update(batch)
            self._lookup_cache.pop(folded, None)
            self._lookup_cache.pop(word, None)
            self._freq[folded] = self._freq.get(folded, 0) + _SEED_FREQ_BONUS
            added.append(folded)
        if added:
            self._index_near()
            self._index_freq_near()
        if added and self._persist_user:
            _append_user_words(added)
        return added

    def ensure_curated(self, words: Iterable[str]) -> list[str]:
        """Guarantee words are in the curated seed + user file (idempotent)."""
        ensured: list[str] = []
        for raw in words:
            word = raw.strip()
            if len(word) < 2:
                continue
            folded = word.casefold()
            batch = {word, folded} | expand_case_forms({folded})
            was_new = folded not in self._seed
            self._seed.update({word, folded})
            self._words.update(batch)
            self._lookup_cache.pop(folded, None)
            self._lookup_cache[folded] = True
            if was_new:
                self._freq[folded] = self._freq.get(folded, 0) + _SEED_FREQ_BONUS
                ensured.append(folded)
        if ensured:
            self._index_near()
            self._index_freq_near()
        if self._persist_user:
            # Always persist approved surface forms so restarts keep them.
            _append_user_words([item.strip().casefold() for item in words if item.strip()])
        return ensured

    @property
    def has_hunspell(self) -> bool:
        return self._hunspell is not None

    def hunspell_knows(self, word: str) -> bool:
        if self._hunspell is None:
            return False
        folded = word.casefold()
        return bool(self._hunspell.lookup(folded) or self._hunspell.lookup(word))

    def in_seed(self, word: str) -> bool:
        folded = word.casefold()
        return word in self._seed or folded in self._seed

    def in_wordlist(self, word: str) -> bool:
        return word in self._words or word.casefold() in self._words

    def contains(self, word: str) -> bool:
        folded = word.casefold()
        if word in self._words or folded in self._words:
            return True
        cached = self._lookup_cache.get(folded)
        if cached is not None:
            return cached
        ok = False
        if self._hunspell is not None:
            ok = bool(self._hunspell.lookup(word) or self._hunspell.lookup(folded))
        self._lookup_cache[folded] = ok
        return ok

    def is_frequent_inflection(self, word: str) -> bool:
        """Frequent stem plus a school case/plural tail (вэбсайт → вэбсайтад)."""
        folded = word.casefold()
        for n in range(len(folded) - 1, 3, -1):
            stem = folded[:n]
            if self.wiki_frequency(stem) < _FREQ_TRUST:
                continue
            if folded in expand_case_forms({stem}):
                return True
            vowel = _last_vowel(stem)
            if vowel in "аяуы":
                link = "а"
            elif vowel in "оё":
                link = "о"
            elif vowel in "эеи":
                link = "э"
            elif vowel in "өү":
                link = "ө"
            else:
                link = ""
            tail = folded[n:]
            if tail in {"д", "нд"} or (link and tail == f"{link}д"):
                return True
            if tail in {"ууд", "үүд", "уудын", "үүдийн"}:
                return True
        return False

    def suggest(self, word: str) -> tuple[str, str] | None:
        hits = self.suggest_many(word, limit=1)
        if not hits:
            return None
        if self.in_wordlist(hits[0]):
            for variant in _collapse_duplicate_letters(word):
                if hits[0] == variant.casefold() or hits[0] == variant:
                    return hits[0], "doubled_letter"
        return hits[0], "nearby_spelling"

    def _index_near(self) -> None:
        buckets: dict[tuple[str, int], list[str]] = {}
        for item in self._words:
            if " " in item or len(item) < 3:
                continue
            buckets.setdefault((item[:1], len(item)), []).append(item)
        self._near = buckets

    def _index_freq_near(self) -> None:
        buckets: dict[tuple[str, int], list[str]] = {}
        for item, count in self._freq.items():
            if " " in item or len(item) < 3 or count < 1:
                continue
            buckets.setdefault((item[:1], len(item)), []).append(item)
        self._freq_near = buckets

    def frequency(self, word: str) -> int:
        folded = word.casefold()
        return self._freq.get(folded, 0) or self._freq.get(word, 0)

    def wiki_frequency(self, word: str) -> int:
        folded = word.casefold()
        return self._wiki_freq.get(folded, 0) or self._wiki_freq.get(word, 0)

    def prefers_established(self, word: str, suggestion: str | None = None) -> bool:
        """Keep a well-attested spelling instead of a rarer Hunspell neighbor."""
        if len(word) < 4:
            return False
        own = self.wiki_frequency(word)
        if own < _FREQ_TRUST:
            return False
        if suggestion is None:
            return True
        return own >= self.wiki_frequency(suggestion)

    def suggest_many(
        self,
        word: str,
        limit: int = 8,
        preferred: set[str] | None = None,
    ) -> list[str]:
        folded = word.casefold()
        if self.contains(folded):
            return []
        found: list[str] = []
        seen = {folded}
        phases = [
            _edit_candidates(folded, inserts=False),
            _consonant_inserts(folded),
            _suffix_vowel_inserts(folded),
        ]
        for batch in phases:
            for candidate, _score in batch:
                if not _usable_candidate(folded, candidate, seen):
                    continue
                if self._accept_suggestion(folded, candidate):
                    seen.add(candidate)
                    found.append(candidate)
            if len(found) >= limit:
                break
        if len(found) < limit:
            for candidate, _score in _wordlist_neighbors(folded, self._near, self._seed):
                if not _usable_candidate(folded, candidate, seen):
                    continue
                if self._accept_suggestion(folded, candidate):
                    seen.add(candidate)
                    found.append(candidate)
        if len(found) < limit:
            for candidate, _score in _edit_candidates(folded, inserts=True):
                if not _usable_candidate(folded, candidate, seen):
                    continue
                if self._accept_suggestion(folded, candidate):
                    seen.add(candidate)
                    found.append(candidate)
        if self._freq_near:
            for candidate, _score in _frequency_neighbors(
                folded, self._freq_near, self.wiki_frequency, _FREQ_TRUST
            ):
                if not _usable_candidate(folded, candidate, seen):
                    continue
                if lookup_misspelling(candidate):
                    continue
                if len(candidate) == len(folded) - 1 and folded[1:] == candidate:
                    continue
                if not (self.in_wordlist(candidate) or self.contains(candidate)):
                    continue
                seen.add(candidate)
                found.append(candidate)
        close = any(_edit_distance(folded, item) <= 1 for item in found)
        if self._hunspell is not None and (not close or len(found) < limit):
            for candidate in _cheap_hunspell_edits(folded):
                if not _usable_candidate(folded, candidate, seen):
                    continue
                seen.add(candidate)
                if not self.contains(candidate):
                    continue
                if lookup_misspelling(candidate):
                    continue
                if len(candidate) == len(folded) - 1 and folded[1:] == candidate:
                    continue
                found.append(candidate)
                if len(found) >= limit:
                    break
        same = [item for item in found if item[:1] == folded[:1]]
        pool = same or found
        trusted = [
            item
            for item in pool
            if (
                self.wiki_frequency(item) >= _FREQ_TRUST
                or self.in_seed(item)
                or self.in_wordlist(item)
                or _edit_distance(folded, item) <= 1
            )
        ]
        if trusted:
            pool = trusted
        liked = {item.casefold() for item in preferred or set()}
        pool.sort(
            key=lambda item: (
                0 if item in liked else 1,
                0 if _is_adjacent_swap(folded, item) else 1,
                _edit_distance(folded, item),
                0 if _keeps_ending(folded, item) else 1,
                _prefix_cut_penalty(folded, item),
                self._rarity(item),
                -self.frequency(item),
                _rank(folded, item),
            )
        )
        pool = _promote_frequent(
            pool,
            folded,
            self.wiki_frequency,
            lambda item: self.in_seed(item) or self.in_wordlist(item),
        )
        ranked = _drop_weaker_extensions(pool, folded)
        chosen: list[str] = []
        for item in ranked:
            dist = _edit_distance(folded, item)
            rarity = self._rarity(item)
            if rarity > 0 and dist > 2 and self.wiki_frequency(item) < _FREQ_TRUST:
                continue
            if rarity > 0 and dist > 1 and len(chosen) >= 3:
                continue
            chosen.append(item)
            if len(chosen) >= limit:
                break
        return chosen

    def _accept_suggestion(self, original: str, candidate: str) -> bool:
        if not self.in_wordlist(candidate):
            return False
        if lookup_misspelling(candidate):
            return False
        if len(candidate) == len(original) - 1 and original[1:] == candidate:
            return False
        if _ou_flip_only(original, candidate) and not self.in_seed(candidate):
            return False
        return True

    def _rarity(self, word: str) -> int:
        folded = word.casefold()
        if folded in self._seed or word in self._seed:
            return 0
        if folded in self._words or word in self._words:
            return 1
        for n in range(len(folded), 3, -1):
            if folded[:n] in self._seed:
                return 2
        return 3

    def nearest(self, word: str) -> str | None:
        folded = word.casefold()
        if self.contains(folded) or len(folded) < 5:
            return None
        hits: list[str] = []
        for candidate in self._words:
            if " " in candidate:
                continue
            if abs(len(candidate) - len(folded)) > 1:
                continue
            if candidate[:1] != folded[:1]:
                continue
            if _is_edit_distance_one(folded, candidate):
                hits.append(candidate)
        unique = list(dict.fromkeys(hits))
        if len(unique) == 1:
            return unique[0]
        return None


def expand_case_forms(words: Iterable[str]) -> set[str]:
    extra: set[str] = set()
    for stem in words:
        if " " in stem or len(stem) < 5:
            continue
        extra.update(_case_forms(stem.casefold()))
    return extra


def _last_vowel(stem: str) -> str | None:
    for ch in reversed(stem):
        if ch in "аэиоуөүяёеюы":
            return ch
    return None


def _drop_last_i(stem: str) -> str:
    """School rule: last-syllable и drops before a vowel-initial suffix."""
    if not stem or stem[-1] in "аэиоуөүяёеюыьъ":
        return stem
    i_at = stem.rfind("и")
    if i_at < 1:
        return stem
    vowels = "аэиоуөүяёеюы"
    if any(ch in vowels for ch in stem[i_at + 1 :]):
        return stem
    if not any(ch in vowels for ch in stem[:i_at]):
        return stem
    dropped = stem[:i_at] + stem[i_at + 1 :]
    if not dropped or dropped[-1] in vowels:
        return stem
    return dropped


def _case_forms(stem: str) -> set[str]:
    vowel = _last_vowel(stem)
    if not stem[-1].isalpha():
        return set()
    if stem[-1] in "аэиоуөүяёеюыьъ":
        if vowel in "өү":
            suffixes = ("г", "ний", "нд", "нөөс", "тэй")
        elif vowel in "эеи":
            suffixes = ("г", "ний", "нд", "нээс", "тэй")
        elif vowel in "оё":
            suffixes = ("г", "ны", "нд", "ноос", "той")
        else:
            suffixes = ("г", "ны", "нд", "наас", "тай")
        return {stem + suffix for suffix in suffixes}
    if vowel in "өү":
        suffixes = ("өөс", "ийн", "ийг", "тэй", "д", "өө")
    elif vowel in "эеи":
        suffixes = ("ээс", "ийн", "ийг", "тэй", "д", "ээ")
    elif vowel in "оё":
        suffixes = ("оос", "ын", "ыг", "той", "д", "оо")
    else:
        suffixes = ("аас", "ын", "ыг", "тай", "д", "аа")
    if stem[-1] in "гжшч":
        suffixes = tuple(
            "ийн" if item == "ын" else "ийг" if item == "ыг" else item for item in suffixes
        )
    forms: set[str] = set()
    for suffix in suffixes:
        base = _drop_last_i(stem) if suffix[:1] in "аэиоуөүяёеюы" else stem
        forms.add(base + suffix)
    if stem[-1] == "н":
        forms.add(stem + "г")
    return forms


_SIMILAR = {
    "о": "өё",
    "ө": "о",
    "у": "ү",
    "ү": "у",
    "э": "е",
    "е": "э",
    "а": "я",
    "я": "а",
    "и": "йы",
    "й": "и",
    "ы": "и",
}
_VOWELS = "аэиоуөүяёею"


def _ou_flip_only(original: str, candidate: str) -> bool:
    if len(original) != len(candidate):
        return False
    flipped = False
    for a, b in zip(original.casefold(), candidate.casefold(), strict=True):
        if a == b:
            continue
        if {a, b} not in ({"о", "ө"}, {"у", "ү"}):
            return False
        flipped = True
    return flipped


_ENDINGS = (
    "өөс",
    "оос",
    "ээс",
    "аас",
    "өөр",
    "оор",
    "ээр",
    "аар",
    "ийн",
    "ийг",
    "үүд",
    "ууд",
    "ын",
    "ыг",
    "өө",
    "оо",
    "ээ",
    "аа",
)


def _keeps_ending(original: str, candidate: str) -> bool:
    for ending in _ENDINGS:
        if original.endswith(ending) and candidate.endswith(ending):
            return True
    return False


def _usable_candidate(original: str, candidate: str, seen: set[str]) -> bool:
    if candidate in seen or " " in candidate:
        return False
    if len(candidate) < 3:
        return False
    if abs(len(candidate) - len(original)) > 2:
        return False
    return True


def _rank(original: str, candidate: str) -> tuple[int, int, int, str]:
    prefix = 0
    for a, b in zip(original, candidate, strict=False):
        if a != b:
            break
        prefix += 1
    return (-prefix, abs(len(original) - len(candidate)), len(candidate), candidate)


def _drop_weaker_extensions(pool: list[str], original: str = "") -> list[str]:
    """Drop stacked case junk like амжилтад → амжилтадд, танилцана → танилцанаг."""
    kept: list[str] = []
    for item in pool:
        extra_junk = False
        for better in kept:
            if not item.startswith(better) or item == better:
                continue
            extra = item[len(better) :]
            if extra == "г":
                if original.endswith("г") and item.endswith("г"):
                    continue
                extra_junk = True
                break
            if extra == "д" and better.endswith("д"):
                extra_junk = True
                break
        if extra_junk or _is_broken_short_dative(item, kept):
            continue
        kept.append(item)
    return kept


def _is_broken_short_dative(item: str, kept: list[str]) -> bool:
    if len(item) < 4 or not item.endswith("д"):
        return False
    if item[-2] in _VOWELS + "ы":
        return False
    stem = item[:-1]
    return any(
        other != item and other.startswith(stem) and other.endswith("д") for other in kept
    )


def _prefix_len(left: str, right: str) -> int:
    n = 0
    for a, b in zip(left, right, strict=False):
        if a != b:
            break
        n += 1
    return n


def _prefix_cut_penalty(original: str, candidate: str) -> int:
    """Prefer not to treat a longer word as just a shorter stem plus junk."""
    if not original.startswith(candidate) or original == candidate:
        return 0
    extra = original[len(candidate) :]
    if extra and extra == candidate[-1] * len(extra):
        return 0
    return 1


def _promote_frequent(
    pool: list[str],
    original: str,
    wiki_frequency: Callable[[str], int],
    is_lexical: Callable[[str], bool],
) -> list[str]:
    """A much more common word may beat a closer Hunspell-only neighbor."""
    if len(pool) < 2:
        return pool
    best = pool[0]
    if is_lexical(best):
        return pool
    best_dist = _edit_distance(original, best)
    best_wiki = max(wiki_frequency(best), 1)
    for item in pool[1:]:
        dist = _edit_distance(original, item)
        extra = dist - best_dist
        if extra not in (1, 2):
            continue
        if _prefix_len(original, item) < 2:
            continue
        needed = 8 if extra == 1 else 20
        if wiki_frequency(item) >= needed * max(best_wiki, 30):
            return [item, *[row for row in pool if row != item]]
    return pool


def _frequency_neighbors(
    word: str,
    buckets: dict[tuple[str, int], list[str]],
    wiki_frequency: Callable[[str], int],
    trust: int,
) -> list[tuple[str, int]]:
    """Looser than wordlist neighbors: attested words at edit distance 1–3."""
    out: list[tuple[str, int]] = []
    n = len(word)
    first = word[:1]
    for length in range(max(1, n - 3), n + 4):
        for candidate in buckets.get((first, length), ()):
            dist = _edit_distance(word, candidate)
            if dist < 1 or dist > 3:
                continue
            freq = wiki_frequency(candidate)
            prefix = _prefix_len(word, candidate)
            if dist == 1:
                out.append((candidate, dist))
            elif dist == 2 and (prefix >= 3 or freq >= trust):
                out.append((candidate, dist))
            elif dist == 3 and freq >= trust and prefix >= 3:
                out.append((candidate, dist))
    return out


def _wordlist_neighbors(
    word: str,
    buckets: dict[tuple[str, int], list[str]],
    seed: set[str] | None = None,
) -> list[tuple[str, int]]:
    known = seed or set()
    out: list[tuple[str, int]] = []
    n = len(word)
    first = word[:1]
    for length in range(max(1, n - 2), n + 3):
        for candidate in buckets.get((first, length), ()):
            dist = _edit_distance(word, candidate)
            if dist == 1:
                out.append((candidate, dist))
            elif dist == 2:
                prefix = _prefix_len(word, candidate)
                if prefix >= 4:
                    out.append((candidate, dist))
            elif dist == 3:
                prefix = _prefix_len(word, candidate)
                if prefix >= 6 and (candidate in known or candidate.casefold() in known):
                    out.append((candidate, dist))
    return out


_CASE_TAILS = ("ийг", "ыг", "ийн", "ын", "аас", "ээс", "оос", "өөс", "нд", "г", "д", "н")


def _suffix_forms(word: str, suffixes: tuple[str, ...]) -> list[tuple[str, str]]:
    """Stem and ending for a suffix, including a following case letter."""
    out: list[tuple[str, str]] = []
    for suffix in suffixes:
        for tail in ("", *_CASE_TAILS):
            ending = suffix + tail
            if not word.endswith(ending) or len(word) < 6 + len(tail):
                continue
            out.append((word[: -len(ending)], ending))
    return out


def _consonant_inserts(word: str) -> list[tuple[str, int]]:
    """Missing letters in common endings, e.g. шаардлатай → шаардлагатай."""
    out: list[tuple[str, int]] = []
    for stem, ending in _suffix_forms(word, ("тай", "тэй", "той")):
        for letter in "глнв":
            out.append((stem + letter + ending, 1))
    return out


def _suffix_vowel_inserts(word: str) -> list[tuple[str, int]]:
    """Missing stem vowel before a suffix, e.g. шаардлагтай → шаардлагатай."""
    out: list[tuple[str, int]] = []
    for stem, ending in _suffix_forms(word, ("тай", "тэй", "той", "гүй")):
        for vowel in _VOWELS:
            out.append((stem + vowel + ending, 1))
    return out


def _cheap_hunspell_edits(word: str) -> list[str]:
    """Deletes, duplicate-letter collapse, and adjacent swaps only — few Hunspell lookups."""
    out: list[str] = []
    for variant in _collapse_duplicate_letters(word):
        out.append(variant)
    for i in range(len(word)):
        out.append(word[:i] + word[i + 1 :])
    for i in range(len(word) - 1):
        out.append(word[:i] + word[i + 1] + word[i] + word[i + 2 :])
    return out


def _edit_candidates(word: str, *, inserts: bool) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    if inserts:
        for i in range(len(word) + 1):
            for vowel in _VOWELS:
                out.append((word[:i] + vowel + word[i:], 2))
        return out
    for variant in _collapse_duplicate_letters(word):
        out.append((variant, 1))
    for i in range(len(word)):
        out.append((word[:i] + word[i + 1 :], 1))
    for i in range(len(word) - 1):
        out.append((word[:i] + word[i + 1] + word[i] + word[i + 2 :], 2))
    for i, ch in enumerate(word):
        for other in _SIMILAR.get(ch, ""):
            out.append((word[:i] + other + word[i + 1 :], 1))
        if ch in _VOWELS or ch in "ыь":
            for vowel in _VOWELS + "ы":
                if vowel != ch:
                    out.append((word[:i] + vowel + word[i + 1 :], 1))
    return out


def _collapse_duplicate_letters(word: str) -> list[str]:
    variants: list[str] = []
    for i in range(len(word) - 1):
        if word[i] != word[i + 1] or not word[i].isalpha():
            continue
        variants.append(word[:i] + word[i + 1 :])
    return variants


def _is_adjacent_swap(left: str, right: str) -> bool:
    if len(left) != len(right) or left == right:
        return False
    diffs = [i for i, (a, b) in enumerate(zip(left, right, strict=True)) if a != b]
    if len(diffs) != 2:
        return False
    i, j = diffs
    return j == i + 1 and left[i] == right[j] and left[j] == right[i]


def _edit_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if abs(len(left) - len(right)) > 3:
        return 99
    prev = list(range(len(right) + 1))
    for i, a in enumerate(left, start=1):
        current = [i]
        for j, b in enumerate(right, start=1):
            current.append(
                min(prev[j] + 1, current[j - 1] + 1, prev[j - 1] + (a != b))
            )
        if min(current) > 3:
            return 99
        prev = current
    return prev[-1]


def _is_edit_distance_one(left: str, right: str) -> bool:
    return _edit_distance(left, right) == 1


def _append_user_words(words: list[str]) -> None:
    path = user_dictionary_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_user_dictionary(path)
    with path.open("a", encoding="utf-8") as handle:
        for word in words:
            if word in existing:
                continue
            handle.write(f"{word}\n")
            existing.add(word)
