# MongolWrite AI

Монгол хэлний бичгийн туслах — албан бичгийн зөв бичих, цэг таслал, кирилл/латин хольц, о/ө у/ү төөрөлдөлтийг шалгана.

V1: вэб editor + дүрмийн engine. AI руу текст илгээдэггүй.

## Local development

```bash
cp .env.example .env
docker compose up -d
cd backend && uv sync --all-extras
python ../scripts/fetch_mn_dictionary.py
uv run uvicorn app.main:app --reload --app-dir .
# other terminal
cd frontend && npm install && npm run dev
```

- App: http://localhost:3000
- API: http://localhost:8000/health
- Docs: http://localhost:8000/docs

## Production (нэг линк)

Frontend болон API нэг порт дээр ажиллана. Hunspell толийг Docker build үед татна.

```bash
cd frontend && NEXT_OUTPUT=export npm run build
cd ../backend && APP_ENV=production uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Эсвэл Docker:

```bash
docker build -t mongolwrite .
docker run -p 8080:8080 mongolwrite
```

Интернэтэд [Fly.io](https://fly.io) дээр:

```bash
fly auth login
fly launch --copy-config --yes --now
```

Сайтын хаяг: `https://mongolwrite.com`

## Tests

## Tests

```bash
cd backend && uv run pytest
cd frontend && npm run lint
```

## Environment

See `.env.example`. Do not put API keys in the repo. `OPENAI_API_KEY` is unused in V1.

## Word list

Зөв бичгийг `mongoltoli.mn` (Их тайлбар толь)-оос хуулдаггүй — тэр бол зохиогчийн эрхтэй тайлбар толь.

Ашиглаж буй эх:

1. [dict-mn](https://github.com/bataak/dict-mn) Hunspell — Firefox/LibreOffice-ийн монгол spellcheck (~75 мянган үндэс)
2. `data/wordlist.txt` — орчин үеийн нэр томьёо (эрсдэл гэх мэт) + тийн ялгалын хэлбэр
3. `data/word_frequency.txt` — Википедиа дээрх үгийн давтамж (засвар сонгоход)

```bash
python3 scripts/fetch_mn_dictionary.py
# optional: refresh frequency from Wikipedia
# uv run --project backend python scripts/build_word_frequency.py
```

## Layout

- `frontend` — Next.js editor
- `backend` — FastAPI + Mongolian language engine
- `data/wordlist.txt` — small overlay list
- `data/word_frequency.txt` — Wikipedia word counts for ranking suggestions
- `data/common_misspellings.txt` — түгээмэл зөв бичгийн алдаа
- `data/user_dictionary.txt` — таны Word/текстээс сурсан хувийн толь (git-д орохгүй)
- `data/hunspell` — dict-mn (Hunspell), Firefox/LibreOffice монгол толь. Их тайлбар толь биш.
- `docs/ARCHITECTURE.md` — architecture
- `infrastructure/compose.yaml` — Postgres + Redis

Хуучин Word (`.docx`) эсвэл `.txt` файлаа «Word файл нээх»-ээр оруулна. Алдаа гэж гараагүй кирилл үгс автоматаар хувийн тольд орно. Буруу гэж гарсан үнэн зөв үгийг баруун талын «Тольд нэмэх»-ээр нэмнэ.
