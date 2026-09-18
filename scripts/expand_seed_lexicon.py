#!/usr/bin/env python3
"""Grow curated seed from Wikipedia frequency + Hunspell acceptance.

The admin «Үгийн сан» count is the curated seed (о/ө · у/ү suggestions),
not the full Hunspell lexicon. This script pulls high-frequency Cyrillic
forms that Hunspell accepts so the trusted list matches real usage.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORDLIST = ROOT / "data" / "wordlist.txt"
FREQUENCY = ROOT / "data" / "word_frequency.txt"
HUNSPELL = ROOT / "data" / "hunspell" / "mn_MN"

# Keep seed large enough for confusable suggestions, small enough to index fast.
MIN_FREQ = 40
MAX_NEW = 12_000
CYRILLIC = re.compile(r"^[А-Яа-яӨөҮүЁё\-']+$")


def load_existing() -> tuple[list[str], set[str]]:
    lines: list[str] = []
    lemmas: set[str] = set()
    if WORDLIST.exists():
        for line in WORDLIST.read_text(encoding="utf-8").splitlines():
            lines.append(line)
            word = line.strip()
            if word and not word.startswith("#"):
                lemmas.add(word.casefold())
    return lines, lemmas


def load_frequency() -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    for line in FREQUENCY.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2 or not parts[-1].isdigit():
            continue
        word, count = parts[0], int(parts[-1])
        if count < MIN_FREQ or not CYRILLIC.match(word):
            continue
        if len(word) < 2:
            continue
        rows.append((word, count))
    rows.sort(key=lambda item: (-item[1], item[0].casefold()))
    return rows


def hunspell_lookup():
    if not HUNSPELL.with_suffix(".dic").exists():
        return None
    from spylls.hunspell import Dictionary

    return Dictionary.from_files(str(HUNSPELL))


def main() -> int:
    header_lines, existing = load_existing()
    comments = [line for line in header_lines if line.startswith("#") or not line.strip()]
    if not any("Expanded" in line for line in comments):
        comments = [
            "# Curated seed for о/ө and у/ү suggestions + admin overview.",
            "# Expanded from mnwiki frequency (forms Hunspell accepts).",
            "# Full acceptance still uses data/hunspell/mn_MN (~600k stems).",
            "",
        ]

    hun = hunspell_lookup()
    if hun is None:
        print("Hunspell missing — run scripts/fetch_mn_dictionary.py first", file=sys.stderr)
        return 1

    kept = sorted(
        {line.strip() for line in header_lines if line.strip() and not line.startswith("#")},
        key=str.casefold,
    )
    added: list[str] = []
    for word, _count in load_frequency():
        folded = word.casefold()
        if folded in existing:
            continue
        try:
            ok = hun.lookup(word) or hun.lookup(folded)
        except Exception:
            ok = False
        if not ok:
            continue
        existing.add(folded)
        added.append(folded)
        if len(added) >= MAX_NEW:
            break

    body = sorted(set(kept) | set(added), key=str.casefold)
    WORDLIST.write_text("\n".join(comments + body) + "\n", encoding="utf-8")
    print(f"seed={len(body)} added={len(added)} path={WORDLIST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
