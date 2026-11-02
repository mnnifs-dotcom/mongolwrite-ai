#!/usr/bin/env python3
"""Grow curated seed from Wikipedia frequency + Hunspell acceptance.

The admin «Үгийн сан» is the curated seed (о/ө · у/ү suggestions + browsing),
not the full Hunspell lexicon (~621k stems). Hunspell already accepts those
forms at check time; dumping every stem would pollute suggestions with rare
productive stacks.

This script pulls high-frequency Cyrillic surface forms that Hunspell accepts
so the trusted list tracks real usage without a full .dic dump.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORDLIST = ROOT / "data" / "wordlist.txt"
FREQUENCY = ROOT / "data" / "word_frequency.txt"
LEGAL_TRUSTED = ROOT / "data" / "legal_trusted.txt"
HUNSPELL = ROOT / "data" / "hunspell" / "mn_MN"

# Large enough for confusable suggestions; small enough to index fast.
# Freq ≥20 ∩ Hunspell is still common Wikipedia usage — safer than dumping .dic.
MIN_FREQ = 20
MAX_NEW = 20_000
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


def load_legal_trusted() -> list[str]:
    if not LEGAL_TRUSTED.exists():
        return []
    out: list[str] = []
    for line in LEGAL_TRUSTED.read_text(encoding="utf-8").splitlines():
        word = line.strip()
        if word and not word.startswith("#") and CYRILLIC.match(word):
            out.append(word.casefold())
    return out


def hunspell_lookup():
    if not HUNSPELL.with_suffix(".dic").exists():
        return None
    from spylls.hunspell import Dictionary

    return Dictionary.from_files(str(HUNSPELL))


def main() -> int:
    header_lines, existing = load_existing()
    comments = [
        "# Curated seed for о/ө and у/ү suggestions + admin «Үгийн сан».",
        "# Expanded from mnwiki frequency ∩ Hunspell (not a full .dic dump).",
        "# Full acceptance still uses data/hunspell/mn_MN (~621k stems).",
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

    # 1) Legal trusted lemmas (already Hunspell-filtered by build_legal_lexicon).
    for word in load_legal_trusted():
        if word in existing:
            continue
        existing.add(word)
        added.append(word)

    # 2) High-frequency Wikipedia forms Hunspell accepts.
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
    print(f"seed={len(body)} added={len(added)} min_freq={MIN_FREQ} path={WORDLIST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
