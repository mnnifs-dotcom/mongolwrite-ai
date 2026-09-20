#!/usr/bin/env python3
"""Rebuild data/legal_laws_index.json.gz from legalinfo.mn/sitemap.xml.

Optional: merge nicer titles from a local HF laws.parquet mirror.
"""

from __future__ import annotations

import gzip
import json
import re
import sys
import urllib.request
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "legal_laws_index.json.gz"
SITEMAP = "https://legalinfo.mn/sitemap.xml"
PARQUET = Path("/tmp/legalinfo/laws.parquet")


def main() -> int:
    print(f"Downloading {SITEMAP} …")
    with urllib.request.urlopen(SITEMAP, timeout=120) as resp:
        xml = resp.read().decode("utf-8", errors="replace")
    locs = re.findall(r"<loc>([^<]+)</loc>", xml)
    by_id: OrderedDict[str, str] = OrderedDict()
    for loc in locs:
        m = re.search(r"lawId=(\d+)", loc) or re.search(r"/mn/detail/(\d+)", loc)
        if not m:
            continue
        lid = m.group(1)
        if lid not in by_id:
            by_id[lid] = f"https://legalinfo.mn/mn/detail?lawId={lid}"

    titles: dict[str, str] = {}
    if PARQUET.is_file():
        try:
            import pyarrow.parquet as pq

            table = pq.read_table(PARQUET)
            for i in range(table.num_rows):
                ident = str(table.column("identifier")[i].as_py() or "").strip()
                title = str(table.column("title")[i].as_py() or "").strip()
                if ident.isdigit() and title and "дэлгэрэнгүй" not in title.lower():
                    titles[ident] = title
        except Exception as exc:  # noqa: BLE001 — best-effort title merge
            print(f"title merge skipped: {exc}", file=sys.stderr)

    laws = [
        {
            "law_id": lid,
            "title": titles.get(lid, f"Хууль #{lid}"),
            "url": url,
        }
        for lid, url in sorted(by_id.items(), key=lambda item: int(item[0]))
    ]
    payload = {
        "source": SITEMAP,
        "count": len(laws),
        "laws": laws,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    OUT.write_bytes(gzip.compress(raw, compresslevel=9))
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes, {len(laws)} laws)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
