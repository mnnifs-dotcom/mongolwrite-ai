from __future__ import annotations

from functools import lru_cache
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def load_misspellings(path: Path | None = None) -> dict[str, str]:
    target = path or (_repo_root() / "data" / "common_misspellings.txt")
    if not target.exists():
        return {}
    mapping: dict[str, str] = {}
    for line in target.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        if "\t" in raw:
            wrong, right = raw.split("\t", 1)
        else:
            parts = raw.split()
            if len(parts) < 2:
                continue
            wrong, right = parts[0], " ".join(parts[1:])
        wrong, right = wrong.strip().casefold(), right.strip()
        if wrong and right and wrong != right.casefold():
            mapping[wrong] = right
    return mapping


_CASE_TAILS = (
    "ийг",
    "ыг",
    "ийн",
    "ын",
    "аас",
    "ээс",
    "оос",
    "өөс",
    "нд",
    "г",
    "д",
    "н",
)


def lookup_misspelling(word: str) -> str | None:
    folded = word.casefold()
    mapping = load_misspellings()
    direct = mapping.get(folded)
    if direct:
        return direct
    for tail in _CASE_TAILS:
        if len(folded) <= len(tail) or not folded.endswith(tail):
            continue
        right = mapping.get(folded[: -len(tail)])
        if right and " " not in right:
            return right + tail
    return None
