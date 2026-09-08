"""Build data/word_frequency.txt from Mongolian Wikipedia.

Uses the public Wikimedia dump (CC BY-SA). Does not scrape mongoltoli.mn.
Suggestions still require a Hunspell or wordlist hit at check time.
"""

from __future__ import annotations

import bz2
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "word_frequency.txt"
VENDOR = ROOT / "data" / "vendor"
DUMP_NAME = "mnwiki-latest-pages-articles.xml.bz2"
DUMP_URL = f"https://dumps.wikimedia.org/mnwiki/latest/{DUMP_NAME}"
WORD_RE = re.compile(r"[А-Яа-яЁёӨөҮү]+")
MIN_COUNT = 2
MIN_LEN = 3
MAX_WORDS = 40_000


def _download(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {DUMP_URL}")
    request = urllib.request.Request(
        DUMP_URL,
        headers={"User-Agent": "MongolWriteAI/1.0 (frequency builder; https://github.com/)"},
    )
    with urllib.request.urlopen(request) as response, path.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    print(f"  {path} ({path.stat().st_size} bytes)")


def _count_dump(path: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    with bz2.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            for match in WORD_RE.finditer(line):
                word = match.group(0).casefold()
                if len(word) >= MIN_LEN:
                    counts[word] += 1
    return counts


def main() -> int:
    backend = ROOT / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    from app.engine.dictionary import load_wordlist
    from app.engine.misspellings import load_misspellings

    dump = VENDOR / DUMP_NAME
    if not dump.exists():
        _download(dump)
    print("Counting Wikipedia tokens …", flush=True)
    counts = _count_dump(dump)
    print(f"  {sum(counts.values())} tokens, {len(counts)} types", flush=True)
    wordlist = {item.casefold() for item in load_wordlist() if len(item.casefold()) >= MIN_LEN}
    kept: list[tuple[int, str]] = [
        (count, word) for word, count in counts.most_common(MAX_WORDS) if count >= MIN_COUNT
    ]
    seen = {word for _, word in kept}
    for word in wordlist:
        if word not in seen:
            kept.append((max(counts.get(word, 0), MIN_COUNT), word))
            seen.add(word)
    for target in load_misspellings().values():
        if " " in target:
            continue
        folded = target.casefold()
        if folded not in seen and len(folded) >= MIN_LEN:
            kept.append((max(counts.get(folded, 0), MIN_COUNT), folded))
            seen.add(folded)
    kept.sort(key=lambda item: (-item[0], item[1]))
    DEST.write_text(
        "# Mongolian Wikipedia surface-form counts (CC BY-SA).\n"
        "# dumps.wikimedia.org/mnwiki — top surface forms; suggestions still require Hunspell.\n"
        + "\n".join(f"{word}\t{count}" for count, word in kept)
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {DEST} ({len(kept)} words)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
