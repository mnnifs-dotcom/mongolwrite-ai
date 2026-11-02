# MongolWrite data

| File | Role |
| --- | --- |
| `wordlist.txt` | Curated seed for о/ө · у/ү suggestions and admin «Үгийн сан». Grown from mnwiki frequency ∩ Hunspell — **not** a full Hunspell dump. |
| `hunspell/mn_MN.*` | Full dict-mn Hunspell (~621k stems) — acceptance at check time, suggestions, candidate harvest. |
| `word_frequency.txt` | Wikipedia surface-form counts (CC BY-SA). |
| `legal_trusted.txt` | High-confidence statute lemmas (auto-merged into curated seed). |
| `legal_doubt.json` | Frequent legal tokens awaiting admin review. |
| `common_misspellings.txt` | Hand-curated typo → correct map. |
| `persist/` | Runtime volume (Fly): candidates, admin-added log, user dictionary, removed tombstones. |

## Curated vs Hunspell

Hunspell knows ~621k stems (often quoted as ~75k base lemmas with huge affix expansion). Those forms are **already accepted** during spell-check via `contains()` → Hunspell lookup.

The curated «Үгийн сан» is a smaller trusted list used for:
- о/ө · у/ү suggestion neighbors
- admin browsing / copy-export
- ranking preferred corrections

Dumping every Hunspell stem into the curated list would flood suggestions with rare productive stacks. Instead we grow from **high-frequency Wikipedia forms ∩ Hunspell**.

Expand seed again:

```bash
python scripts/fetch_mn_dictionary.py   # if needed
python scripts/expand_seed_lexicon.py
```
