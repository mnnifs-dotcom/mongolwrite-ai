from __future__ import annotations

import gzip
import json
from pathlib import Path

from app.engine import legal_laws


def test_list_laws_from_index(tmp_path: Path, monkeypatch) -> None:
    payload = {
        "source": "test",
        "count": 2,
        "laws": [
            {"law_id": "10", "title": "ӨРШӨӨЛ ҮЗҮҮЛЭХ ТУХАЙ", "url": "https://legalinfo.mn/mn/detail?lawId=10"},
            {"law_id": "12701", "title": "ШҮҮХИЙН ШИЙДВЭР ГҮЙЦЭТГЭХ ТУХАЙ", "url": "https://legalinfo.mn/mn/detail?lawId=12701"},
        ],
    }
    path = tmp_path / "legal_laws_index.json.gz"
    path.write_bytes(gzip.compress(json.dumps(payload, ensure_ascii=False).encode("utf-8")))
    persist = tmp_path / "persist"
    persist.mkdir()
    monkeypatch.setattr(legal_laws, "laws_index_path", lambda: path)
    monkeypatch.setattr(legal_laws, "ingested_laws_path", lambda: persist / "legal_laws_ingested.json")
    legal_laws.clear_laws_cache()

    page = legal_laws.list_laws(q="", offset=0, limit=10)
    assert page["total"] == 2
    assert page["items"][0]["law_id"] == "10"
    assert page["ingested_count"] == 0
    assert page["remaining_count"] == 2

    found = legal_laws.list_laws(q="12701", offset=0, limit=10)
    assert found["total"] == 1
    assert found["items"][0]["title"].startswith("ШҮҮХИЙН")

    # Unknown id still surfaces when searched exactly.
    orphan = legal_laws.list_laws(q="999999", offset=0, limit=5)
    assert orphan["total"] == 1
    assert orphan["items"][0]["law_id"] == "999999"


def test_ingested_laws_disappear_from_list(tmp_path: Path, monkeypatch) -> None:
    payload = {
        "source": "test",
        "count": 2,
        "laws": [
            {"law_id": "10", "title": "ӨРШӨӨЛ ҮЗҮҮЛЭХ ТУХАЙ", "url": "https://legalinfo.mn/mn/detail?lawId=10"},
            {"law_id": "12701", "title": "ШҮҮХИЙН ШИЙДВЭР ГҮЙЦЭТГЭХ ТУХАЙ", "url": "https://legalinfo.mn/mn/detail?lawId=12701"},
        ],
    }
    path = tmp_path / "legal_laws_index.json.gz"
    path.write_bytes(gzip.compress(json.dumps(payload, ensure_ascii=False).encode("utf-8")))
    persist = tmp_path / "persist"
    persist.mkdir()
    monkeypatch.setattr(legal_laws, "laws_index_path", lambda: path)
    monkeypatch.setattr(legal_laws, "ingested_laws_path", lambda: persist / "legal_laws_ingested.json")
    legal_laws.clear_laws_cache()

    legal_laws.mark_law_ingested("10", title="ӨРШӨӨЛ ҮЗҮҮЛЭХ ТУХАЙ")
    page = legal_laws.list_laws(q="", offset=0, limit=10)
    assert page["total"] == 1
    assert page["items"][0]["law_id"] == "12701"
    assert page["ingested_count"] == 1
    assert page["remaining_count"] == 1

    # Exact search of an ingested id must not bring it back.
    gone = legal_laws.list_laws(q="10", offset=0, limit=5)
    assert gone["total"] == 0
    assert gone["items"] == []


def test_html_label_extraction() -> None:
    html = """
    <html><head><title>ЖИШЭЭ ХУУЛЬ</title></head><body>
    <label class="line-clamp-1">МОНГОЛ УЛСЫН ХУУЛЬ</label>
    <label class="line-clamp-1">1 ДҮГЭЭР ЗҮЙЛ.ЗОРИЛТ</label>
    <label class="line-clamp-1">1.1.ЭНЭ ХУУЛИЙН ЗОРИЛТ НЬ ИРГЭНИЙ ЭРХИЙГ ХАМГААЛАХАД ОРШИНО.</label>
    <label class="line-clamp-1">Pdf</label>
    <label class="line-clamp-1">Нэвтрэх</label>
    </body></html>
    """
    title, text = legal_laws._html_to_plain_labels(html)
    assert title == "ЖИШЭЭ ХУУЛЬ"
    assert "ЗОРИЛТ" in text
    assert "Нэвтрэх" not in text
    assert "Pdf" not in text
