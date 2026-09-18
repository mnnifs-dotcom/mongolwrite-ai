# MongolWrite data

| File | Role |
| --- | --- |
| `wordlist.txt` | Curated seed (~12k) for о/ө · у/ү suggestions and admin «Найдвартай үгийн сан». Grown from mnwiki frequency + Hunspell. |
| `hunspell/mn_MN.*` | Full dict-mn Hunspell (~621k stems) — acceptance, suggestions, candidate harvest. |
| `word_frequency.txt` | Wikipedia surface-form counts (CC BY-SA). |
| `common_misspellings.txt` | Hand-curated typo → correct map. |
| `persist/` | Runtime volume (Fly): candidates, admin-added log, user dictionary. |

Expand seed again:

```bash
python scripts/fetch_mn_dictionary.py
python scripts/expand_seed_lexicon.py
```
