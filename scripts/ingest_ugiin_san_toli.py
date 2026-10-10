#!/usr/bin/env python3
"""Ingest common headwords + toli.gov.mn inflectional variants into the seed.

Reads a parsed үгийн сан.docx export (JSON of {text, links}), keeps only
headwords that appear often in mnwiki frequency, fetches each linked word
page, and collects the headword plus single-token «Хувилал» forms.

Rare / archaic toli entries are skipped so the curated seed does not grow
with forms users will treat as false corrections.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import sys
import time
import urllib.error
import urllib.request
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORDLIST = ROOT / "data" / "wordlist.txt"
FREQUENCY = ROOT / "data" / "word_frequency.txt"

CYRILLIC = re.compile(r"^[А-Яа-яӨөҮүЁё\-']+$")
SLUG_RE = re.compile(r"^[A-Za-z0-9]{8,}$")
MIN_FREQ = 20
MIN_USAGE_CIRCLES = 1
MAX_WORKERS = 12
USER_AGENT = "MongolWriteLexiconBot/1.0 (+https://mongolwrite.com; lexicon seed)"


def load_frequency(path: Path) -> dict[str, int]:
    freq: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2 or not parts[-1].isdigit():
            continue
        freq[parts[0].casefold()] = int(parts[-1])
    return freq


def load_existing(path: Path) -> tuple[list[str], set[str]]:
    lines: list[str] = []
    lemmas: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            lines.append(line)
            word = line.strip()
            if word and not word.startswith("#"):
                lemmas.add(word.casefold())
    return lines, lemmas


def headword(text: str) -> str | None:
    match = re.match(r"^([^\s\[]+)", text.strip())
    if not match:
        return None
    return match.group(1).casefold()


def word_slugs(links: list) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in links or []:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        url = str(item[1])
        if "/w/" not in url:
            continue
        slug = url.rstrip("/").split("/")[-1].split("?")[0]
        if SLUG_RE.match(slug) and slug not in seen:
            seen.add(slug)
            out.append(slug)
    return out


def usage_circles(html: str) -> int:
    match = re.search(r'class="word-usage">(.*?)</(?:span|div)>', html, re.S)
    if not match:
        return 0
    block = match.group(1)
    empty = block.count("fa-circle-o")
    return block.count("fa-circle") - empty


# Postpositions toli often separates with NBSP — keep as separate tokens.
_NEVER_JOIN = frozenset({"рүү", "руу", "лүү", "луу"})


def _normalize_inflected(raw: str) -> list[str]:
    """Join stem+suffix split by NBSP; keep postpositions / multi-word forms."""
    form = unescape(raw).strip()
    # Foreign-stem case forms: «геологи\\xa0йг» → геологийг
    # Direction postpositions: «акробат\\xa0рүү» stay two tokens.
    chunks = re.split(r"\s*\xa0\s*", form)
    if len(chunks) >= 2:
        rebuilt = [chunks[0]]
        for chunk in chunks[1:]:
            folded = chunk.casefold()
            if folded in _NEVER_JOIN or len(folded) > 6:
                rebuilt.append(" ")
                rebuilt.append(chunk)
            else:
                rebuilt.append(chunk)
        form = "".join(rebuilt)
    form = re.sub(r"\s+", " ", form).strip(".,;:!?\"'()[]«»")
    if not form:
        return []
    if " " in form:
        return [part.casefold() for part in form.split() if part]
    return [form.casefold()]


def parse_page(html: str) -> tuple[str, int, set[str]]:
    head_match = re.search(r'<div class="word">\s*([^<]+)', html)
    head = unescape(head_match.group(1)).strip().casefold() if head_match else ""
    filled = usage_circles(html)
    tokens: set[str] = set()
    if head and CYRILLIC.match(head) and len(head) >= 2:
        tokens.add(head)
    for raw in re.findall(r'class="word-inflected"[^>]*>([^<]+)', html):
        for token in _normalize_inflected(raw):
            if CYRILLIC.match(token) and len(token) >= 2:
                tokens.add(token)
    return head, filled, tokens


def fetch(slug: str, cache_dir: Path | None) -> str:
    if cache_dir is not None:
        cached = cache_dir / f"{slug}.html"
        if cached.exists() and cached.stat().st_size > 500:
            return cached.read_text(encoding="utf-8", errors="ignore")
    url = f"https://toli.gov.mn/w/{slug}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=25) as response:
        html = response.read().decode("utf-8", errors="ignore")
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / f"{slug}.html").write_text(html, encoding="utf-8")
    return html


def collect_slugs(entries: list, freq: dict[str, int], min_freq: int) -> dict[str, list[str]]:
    head_to_slugs: dict[str, list[str]] = {}
    for entry in entries:
        head = headword(str(entry.get("text") or ""))
        if not head or freq.get(head, 0) < min_freq:
            continue
        slugs = word_slugs(entry.get("links") or [])
        if not slugs:
            continue
        bucket = head_to_slugs.setdefault(head, [])
        for slug in slugs:
            if slug not in bucket:
                bucket.append(slug)
    return head_to_slugs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--entries",
        type=Path,
        default=Path("/tmp/ugiin_san_entries.json"),
        help="Parsed docx JSON",
    )
    parser.add_argument("--min-freq", type=int, default=MIN_FREQ)
    parser.add_argument("--min-usage", type=int, default=MIN_USAGE_CIRCLES)
    parser.add_argument("--cache-dir", type=Path, default=Path("/tmp/toli_cache"))
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Collect forms but do not write wordlist.txt",
    )
    parser.add_argument(
        "--out-forms",
        type=Path,
        default=Path("/tmp/toli_common_forms.txt"),
        help="Write collected forms here for inspection",
    )
    args = parser.parse_args()

    if not args.entries.exists():
        print(f"Missing entries JSON: {args.entries}", file=sys.stderr)
        return 1

    entries = json.loads(args.entries.read_text(encoding="utf-8"))
    freq = load_frequency(FREQUENCY)
    head_to_slugs = collect_slugs(entries, freq, args.min_freq)
    slug_heads: dict[str, set[str]] = {}
    for head, slugs in head_to_slugs.items():
        for slug in slugs:
            slug_heads.setdefault(slug, set()).add(head)

    slugs = sorted(slug_heads)
    print(
        f"common heads={len(head_to_slugs)} pages={len(slugs)} "
        f"min_freq={args.min_freq}",
        flush=True,
    )

    collected: set[str] = set()
    kept_pages = 0
    errors = 0
    started = time.time()

    def work(slug: str) -> tuple[str, str | None, int, set[str]]:
        try:
            html = fetch(slug, args.cache_dir)
            head, filled, tokens = parse_page(html)
            return slug, None, filled, tokens
        except Exception as exc:  # noqa: BLE001 — network crawl
            return slug, f"{type(exc).__name__}: {exc}", 0, set()

    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(work, slug) for slug in slugs]
        for fut in concurrent.futures.as_completed(futures):
            slug, err, filled, tokens = fut.result()
            done += 1
            if err:
                errors += 1
            else:
                expected = slug_heads.get(slug, set())
                # Keep official forms when the page is marked used, or the
                # linked head is already known-common from Wikipedia.
                wiki_ok = any(freq.get(h, 0) >= args.min_freq for h in expected)
                if filled >= args.min_usage or wiki_ok:
                    collected.update(tokens)
                    kept_pages += 1
            if done % 100 == 0 or done == len(slugs):
                print(
                    f"  {done}/{len(slugs)} kept_pages={kept_pages} "
                    f"forms={len(collected)} errors={errors} "
                    f"elapsed={time.time()-started:.0f}s",
                    flush=True,
                )

    args.out_forms.write_text(
        "\n".join(sorted(collected, key=str.casefold)) + ("\n" if collected else ""),
        encoding="utf-8",
    )
    print(f"wrote {args.out_forms} ({len(collected)} forms)", flush=True)

    _header_lines, existing = load_existing(WORDLIST)
    added = sorted(
        (word for word in collected if word not in existing),
        key=str.casefold,
    )
    print(f"new for seed: {len(added)} (already had {len(collected) - len(added)})")

    if args.dry_run:
        print("dry-run: not writing wordlist.txt")
        print("sample new:", added[:40])
        return 0

    comments = [
        "# Curated seed for о/ө and у/ү suggestions + admin «Үгийн сан».",
        "# Expanded from mnwiki frequency ∩ Hunspell (not a full .dic dump).",
        "# Plus common toli.gov.mn headwords/variants from үгийн сан.docx.",
        "# Full acceptance still uses data/hunspell/mn_MN (~621k stems).",
        "",
    ]
    kept = sorted(existing | set(added), key=str.casefold)
    WORDLIST.write_text("\n".join(comments + kept) + "\n", encoding="utf-8")
    print(f"updated {WORDLIST}: total={len(kept)} (+{len(added)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
