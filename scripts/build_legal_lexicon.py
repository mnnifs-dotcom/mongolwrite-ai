#!/usr/bin/env python3
"""Build conservative legalinfo.mn lexicon artifacts from the public HF mirror.

Trusted (auto lexicon): Hunspell-accepted + wiki frequency + high legal DF.
Doubt (admin queue): frequent in laws but not safe enough to auto-merge.

Source: Hugging Face endomorphosis/ipfs_mongolia_laws (articles scraped from
legalinfo.mn). Official legalinfo.mn texts remain authoritative.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DATA = ROOT / "data"
OUT_TRUSTED = DATA / "legal_trusted.txt"
OUT_DOUBT = DATA / "legal_doubt.json"
PARQUET_URL = (
    "https://huggingface.co/datasets/endomorphosis/ipfs_mongolia_laws/"
    "resolve/main/data/articles.parquet"
)

# Dual evidence required for automatic curated-lexicon merge.
MIN_LEGAL_DF_TRUSTED = 100
MIN_WIKI_TRUSTED = 50
# Admin review queue — frequent but not dual-confirmed.
MIN_LEGAL_DF_DOUBT = 40
MIN_LEGAL_DF_DOUBT_NO_HUN = 150
MIN_WIKI_DOUBT_NO_HUN = 80
MAX_DOUBT = 500

CYR_WORD = re.compile(r"[А-ЯӨҮЁа-яөүё]{3,}")

# Chrome / portal noise often embedded in scraped pages.
UI_JUNK = {
    "нэвтрэх",
    "бүртгүүлэх",
    "сэргээх",
    "илгээх",
    "имэйл",
    "регистрийн",
    "тусламж",
    "дэлгэрэнгүй",
    "хайлт",
    "эмхэтгэл",
    "сонордуулга",
    "мобайл",
    "порталын",
    "бүртгэл",
    "хэлэлцүүлэг",
    "сонирхлын",
}


def _download_parquet(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        return dest
    print(f"Downloading {PARQUET_URL} …")
    urllib.request.urlretrieve(PARQUET_URL, dest)
    return dest


def _doc_freq(texts: list[str]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for raw in texts:
        text = str(raw or "")
        if len(text) < 40:
            continue
        seen: set[str] = set()
        for match in CYR_WORD.findall(text):
            word = match.casefold()
            if word in UI_JUNK:
                continue
            if word not in seen:
                seen.add(word)
                counts[word] += 1
    return counts


def main() -> int:
    sys.path.insert(0, str(BACKEND))
    import pyarrow.parquet as pq

    from app.engine.confusables import _variants
    from app.engine.dictionary import DictionaryProvider, _FREQ_TRUST
    from app.engine.misspellings import lookup_misspelling
    from app.engine.spelling import _is_implausible

    parquet = _download_parquet(Path("/tmp/legalinfo/articles.parquet"))
    texts = pq.read_table(parquet).column("text").to_pylist()
    freq = _doc_freq(texts)
    dictionary = DictionaryProvider()

    trusted: list[tuple[str, int, int]] = []
    doubt: list[dict[str, object]] = []

    def better_variant(word: str, wiki: int) -> str | None:
        best = ""
        best_wiki = 0
        for variant in _variants(word, limit=16):
            vwiki = dictionary.wiki_frequency(variant)
            known = dictionary.in_seed(variant) or dictionary.in_wordlist(variant)
            if (known or vwiki >= _FREQ_TRUST) and vwiki > wiki + 20 and vwiki > best_wiki:
                best = variant
                best_wiki = vwiki
        return best or None

    for word, legal_df in freq.most_common():
        if dictionary.in_seed(word):
            continue
        if lookup_misspelling(word) or _is_implausible(word):
            continue
        hun_ok = dictionary.hunspell_knows(word)
        wiki = dictionary.wiki_frequency(word)
        rival = better_variant(word, wiki)
        if rival:
            if legal_df >= MIN_LEGAL_DF_DOUBT:
                doubt.append(
                    {
                        "word": word,
                        "folded": word,
                        "legal_df": legal_df,
                        "wiki": wiki,
                        "tier": "doubt",
                        "reason": f"legalinfo · «{rival}» илүү түгээмэл — админ шалгана",
                        "suggestion": rival,
                    }
                )
            continue

        # Trusted: Hunspell + Wikipedia + legal corpus agreement.
        if hun_ok and wiki >= MIN_WIKI_TRUSTED and legal_df >= MIN_LEGAL_DF_TRUSTED:
            trusted.append((word, legal_df, wiki))
            continue

        # Doubt: frequent in official laws, needs human review.
        if legal_df >= MIN_LEGAL_DF_DOUBT and (
            hun_ok or wiki >= MIN_WIKI_DOUBT_NO_HUN or legal_df >= MIN_LEGAL_DF_DOUBT_NO_HUN
        ):
            reason = (
                "legalinfo · Hunspell зөвшөөрсөн, админ баталгаажуулна"
                if hun_ok
                else "legalinfo · хуульд түгээмэл, Hunspell мэдэхгүй — админ шалгана"
            )
            doubt.append(
                {
                    "word": word,
                    "folded": word,
                    "legal_df": legal_df,
                    "wiki": wiki,
                    "tier": "doubt",
                    "reason": reason,
                    "suggestion": "",
                }
            )

    doubt.sort(key=lambda row: int(row["legal_df"]), reverse=True)
    doubt = doubt[:MAX_DOUBT]
    trusted.sort(key=lambda row: row[1], reverse=True)

    DATA.mkdir(parents=True, exist_ok=True)
    OUT_TRUSTED.write_text(
        "\n".join(word for word, _, _ in trusted) + ("\n" if trusted else ""),
        encoding="utf-8",
    )
    OUT_DOUBT.write_text(
        json.dumps(
            {
                "source": "legalinfo.mn via HF ipfs_mongolia_laws articles",
                "rules": {
                    "trusted": "hunspell AND wiki>=50 AND legal_df>=100",
                    "doubt": "frequent legal tokens not meeting trusted",
                    "max_doubt": MAX_DOUBT,
                },
                "trusted_count": len(trusted),
                "doubt_count": len(doubt),
                "items": doubt,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {OUT_TRUSTED} ({len(trusted)} trusted)")
    print(f"Wrote {OUT_DOUBT} ({len(doubt)} doubt)")
    for word, legal_df, wiki in trusted[:15]:
        print(f"  trusted {word} df={legal_df} wiki={wiki}")

    # Append trusted lemmas into shipped seed wordlist (idempotent).
    wordlist = DATA / "wordlist.txt"
    existing = {
        line.strip().casefold()
        for line in wordlist.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    append = [word for word, _, _ in trusted if word not in existing]
    if append:
        with wordlist.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(append) + "\n")
        print(f"Appended {len(append)} trusted lemmas to {wordlist}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
