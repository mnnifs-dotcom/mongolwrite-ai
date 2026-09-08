from __future__ import annotations

from functools import lru_cache
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def frequency_path() -> Path:
    return _repo_root() / "data" / "word_frequency.txt"


@lru_cache(maxsize=1)
def load_frequency(path: Path | None = None) -> dict[str, int]:
    """Surface-form counts from Mongolian Wikipedia plus seed boosts in the file."""
    target = path or frequency_path()
    if not target.exists():
        return {}
    counts: dict[str, int] = {}
    for line in target.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        if "\t" in raw:
            word, _, rest = raw.partition("\t")
        else:
            parts = raw.split()
            if len(parts) < 2:
                continue
            word, rest = parts[0], parts[1]
        word = word.strip().casefold()
        if not word:
            continue
        try:
            count = int(rest.strip().split()[0])
        except ValueError:
            continue
        if count > 0:
            counts[word] = max(counts.get(word, 0), count)
    return counts
