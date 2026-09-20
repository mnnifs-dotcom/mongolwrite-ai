"""legalinfo.mn law catalog + per-law fetch/ingest into the lexicon."""

from __future__ import annotations

import gzip
import json
import logging
import re
import threading
from datetime import datetime, timezone
from functools import lru_cache
from html import unescape
from pathlib import Path
from typing import Any

import httpx

from app.engine.dictionary import persist_dir
from app.engine.hunspell_candidates import record_admin_added, record_from_text
from app.engine.learn import learn_accepted_words
from app.engine.pipeline import LanguageEngine

_log = logging.getLogger(__name__)
_ingested_lock = threading.Lock()

_LAW_ID_RE = re.compile(r"^\d{1,16}$")
_LABEL_RE = re.compile(
    r'<label[^>]*class="[^"]*line-clamp-1[^"]*"[^>]*>(.*?)</label>',
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_TITLE_RE = re.compile(r"<title[^>]*>([^<]+)</title>", re.IGNORECASE)
_CYR_WORD = re.compile(r"[А-ЯӨҮЁа-яөүё]{3,}")

# Portal chrome that shows up in scraped labels / HF mirrors.
_UI_JUNK = {
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
    "сонсох",
    "хэвлэх",
    "хуваалцах",
    "pdf",
    "word",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def laws_index_path() -> Path:
    root = _repo_root() / "data"
    gz = root / "legal_laws_index.json.gz"
    if gz.is_file():
        return gz
    return root / "legal_laws_index.json"


def ingested_laws_path() -> Path:
    return persist_dir() / "legal_laws_ingested.json"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_ingested_map() -> dict[str, dict[str, Any]]:
    path = ingested_laws_path()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(raw, dict) and isinstance(raw.get("laws"), dict):
        out: dict[str, dict[str, Any]] = {}
        for key, row in raw["laws"].items():
            lid = str(key).strip()
            if not lid.isdigit():
                continue
            if isinstance(row, dict):
                out[lid] = row
            else:
                out[lid] = {"law_id": lid}
        return out
    # Legacy: {"ids": ["10", …]}
    if isinstance(raw, dict) and isinstance(raw.get("ids"), list):
        return {
            str(item).strip(): {"law_id": str(item).strip()}
            for item in raw["ids"]
            if str(item).strip().isdigit()
        }
    return {}


def _save_ingested_map(rows: dict[str, dict[str, Any]]) -> None:
    path = ingested_laws_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"laws": rows, "count": len(rows)}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ingested_law_ids() -> set[str]:
    with _ingested_lock:
        return set(_load_ingested_map().keys())


def mark_law_ingested(
    law_id: str,
    *,
    title: str = "",
    url: str = "",
    added_to_lexicon: int = 0,
    queued_candidates: int = 0,
) -> None:
    """Record a successful ingest so the law disappears from the admin list."""
    lid = str(law_id).strip()
    if not _LAW_ID_RE.match(lid):
        return
    with _ingested_lock:
        rows = _load_ingested_map()
        prev = rows.get(lid) or {}
        rows[lid] = {
            "law_id": lid,
            "title": title or str(prev.get("title") or f"Хууль #{lid}"),
            "url": url or str(prev.get("url") or law_url(lid)),
            "added_to_lexicon": int(added_to_lexicon),
            "queued_candidates": int(queued_candidates),
            "ingested_at": _now(),
        }
        _save_ingested_map(rows)


@lru_cache(maxsize=1)
def _load_index() -> dict[str, Any]:
    path = laws_index_path()
    if not path.is_file():
        return {"source": None, "count": 0, "laws": []}
    raw = path.read_bytes()
    if path.suffix == ".gz" or path.name.endswith(".json.gz"):
        raw = gzip.decompress(raw)
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        return {"source": None, "count": 0, "laws": []}
    laws = data.get("laws")
    if not isinstance(laws, list):
        laws = []
    return {
        "source": data.get("source"),
        "count": int(data.get("count") or len(laws)),
        "laws": laws,
    }


def clear_laws_cache() -> None:
    _load_index.cache_clear()


def law_url(law_id: str) -> str:
    return f"https://legalinfo.mn/mn/detail?lawId={law_id}"


def list_laws(
    *,
    q: str = "",
    offset: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    """Paginated searchable catalog of legalinfo.mn law links.

    Already-ingested laws are omitted so the admin queue only shows work left.
    """
    index = _load_index()
    laws = index.get("laws") or []
    done = ingested_law_ids()
    if done:
        laws = [
            row
            for row in laws
            if isinstance(row, dict) and str(row.get("law_id") or "") not in done
        ]
    query = q.strip().casefold()
    if query:
        filtered: list[dict[str, Any]] = []
        exact: list[dict[str, Any]] = []
        for row in laws:
            if not isinstance(row, dict):
                continue
            law_id = str(row.get("law_id") or "")
            title = str(row.get("title") or "")
            if law_id.casefold() == query:
                exact.append(row)
            elif query in law_id.casefold() or query in title.casefold():
                filtered.append(row)
        # Exact law_id match: include even if missing from the shipped index,
        # but never re-queue an already ingested law.
        if _LAW_ID_RE.match(query) and not exact and query not in done:
            exact.append(
                {
                    "law_id": query,
                    "title": f"Хууль #{query}",
                    "url": law_url(query),
                }
            )
        laws = exact + filtered

    total = len(laws)
    offset = max(0, offset)
    limit = max(1, min(200, limit))
    page = laws[offset : offset + limit]
    items = [
        {
            "law_id": str(row.get("law_id") or ""),
            "title": str(row.get("title") or f"Хууль #{row.get('law_id')}"),
            "url": str(row.get("url") or law_url(str(row.get("law_id") or ""))),
            "article_count": int(row.get("article_count") or 0),
        }
        for row in page
        if isinstance(row, dict) and str(row.get("law_id") or "").isdigit()
    ]
    catalog_count = int(index.get("count") or 0)
    ingested_count = len(done)
    return {
        "items": items,
        "total": total,
        "offset": offset,
        "limit": limit,
        "source": index.get("source"),
        "catalog_count": catalog_count,
        "ingested_count": ingested_count,
        "remaining_count": max(0, catalog_count - ingested_count),
    }


def _html_to_plain_labels(html: str) -> tuple[str, str]:
    """Extract statute text + page title from a legalinfo detail page."""
    title_match = _TITLE_RE.search(html)
    title = unescape(title_match.group(1)).strip() if title_match else ""
    title = re.sub(r"\s+", " ", title)

    parts: list[str] = []
    for raw in _LABEL_RE.findall(html):
        text = unescape(_TAG_RE.sub(" ", raw))
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 3:
            continue
        folded = text.casefold()
        if folded in _UI_JUNK:
            continue
        # Skip pure Latin UI crumbs.
        if not _CYR_WORD.search(text):
            continue
        parts.append(text)

    body = "\n".join(parts)
    return title, body


def fetch_law_text(law_id: str, *, timeout: float = 90.0) -> dict[str, Any]:
    """Download one legalinfo.mn law and return cleaned Cyrillic body text."""
    lid = str(law_id).strip()
    if not _LAW_ID_RE.match(lid):
        raise ValueError("Буруу lawId")
    url = law_url(lid)
    headers = {
        "User-Agent": "MongolWriteAdmin/1.0 (+https://mongolwrite.com; legal lexicon)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "mn,en;q=0.8",
    }
    with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
        response = client.get(url)
    if response.status_code >= 400:
        raise RuntimeError(f"legalinfo хариу {response.status_code}")
    html = response.text
    title, text = _html_to_plain_labels(html)
    if len(text) < 80:
        raise RuntimeError("Хуулийн текст олдсонгүй (хуудас хоосон эсвэл бүтэц өөрчлөгдсөн)")
    return {
        "law_id": lid,
        "title": title or f"Хууль #{lid}",
        "url": url,
        "text": text,
        "char_count": len(text),
        "line_count": text.count("\n") + 1 if text else 0,
    }


def ingest_law(engine: LanguageEngine, law_id: str) -> dict[str, Any]:
    """Fetch a law, run the checker, add accepted words to the lexicon.

    Also harvests missing forms into the Hunspell candidate queues for review.
    Successful ingest removes the law from the admin pending list.
    """
    fetched = fetch_law_text(law_id)
    text = fetched["text"]
    # Cap extremely large pages so one click cannot stall the machine.
    if len(text) > 900_000:
        text = text[:900_000]

    added = learn_accepted_words(engine, text)
    if added:
        engine.dictionary.ensure_curated(added)
        record_admin_added(added)

    queued = record_from_text(engine, text)

    mark_law_ingested(
        fetched["law_id"],
        title=fetched["title"],
        url=fetched["url"],
        added_to_lexicon=len(added),
        queued_candidates=queued,
    )

    result = {
        "law_id": fetched["law_id"],
        "title": fetched["title"],
        "url": fetched["url"],
        "char_count": fetched["char_count"],
        "line_count": fetched["line_count"],
        "added_to_lexicon": len(added),
        "added_words": added[:80],
        "queued_candidates": queued,
        "removed_from_list": True,
    }
    _log.info(
        "legalinfo ingest lawId=%s added=%s queued=%s chars=%s",
        fetched["law_id"],
        len(added),
        queued,
        fetched["char_count"],
    )
    return result
