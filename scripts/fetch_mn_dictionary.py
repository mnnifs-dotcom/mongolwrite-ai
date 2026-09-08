"""Download the open Mongolian Hunspell dictionary (dict-mn).

mongoltoli.mn (Их тайлбар толь) is a copyrighted explanatory dictionary.
We do not scrape it. Spellchecking uses bataak/dict-mn instead: ~75k stems
and Hunspell affixes, the same lexicon Firefox/LibreOffice use.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "hunspell"
BASE = "https://raw.githubusercontent.com/bataak/dict-mn/main"
FILES = {
    "mn_MN.aff": f"{BASE}/mn_MN/mn_MN.aff",
    "mn_MN.dic": f"{BASE}/mn_MN/mn_MN.dic",
    "README_mn_MN.txt": f"{BASE}/mn_MN/README_mn_MN.txt",
    "LICENSE": f"{BASE}/LICENSE",
}


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        target = DEST / name
        print(f"Downloading {name} …")
        urllib.request.urlretrieve(url, target)
        print(f"  {target} ({target.stat().st_size} bytes)")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
