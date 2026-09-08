# Seed wordlist for о/ө and у/ү suggestions.
# Not a full Hunspell lexicon. Unknown words are not auto-flagged.

`word_frequency.txt` — Mongolian Wikipedia surface-form counts (CC BY-SA,
dumps.wikimedia.org/mnwiki). Used to pick the most likely correction among
valid Hunspell/wordlist neighbors. Rebuild with:

```bash
uv run --project backend python scripts/build_word_frequency.py
```
