from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from app.engine import legal_laws


@pytest.fixture()
def laws_env(tmp_path: Path, monkeypatch):
    payload = {
        "source": "test",
        "count": 3,
        "laws": [
            {"law_id": "10", "title": "ӨРШӨӨЛ ҮЗҮҮЛЭХ ТУХАЙ", "url": "https://legalinfo.mn/mn/detail?lawId=10"},
            {"law_id": "15", "title": "ҮНЭТ ЦААСНЫ ЗАХ ЗЭЭЛИЙН ТУХАЙ", "url": "https://legalinfo.mn/mn/detail?lawId=15"},
            {"law_id": "12701", "title": "ШҮҮХИЙН ШИЙДВЭР ГҮЙЦЭТГЭХ ТУХАЙ", "url": "https://legalinfo.mn/mn/detail?lawId=12701"},
        ],
    }
    path = tmp_path / "legal_laws_index.json.gz"
    path.write_bytes(gzip.compress(json.dumps(payload, ensure_ascii=False).encode("utf-8")))
    persist = tmp_path / "persist"
    persist.mkdir()
    monkeypatch.setattr(legal_laws, "laws_index_path", lambda: path)
    monkeypatch.setattr(legal_laws, "ingested_laws_path", lambda: persist / "legal_laws_ingested.json")
    monkeypatch.setattr(legal_laws, "failed_laws_path", lambda: persist / "legal_laws_failed.json")
    legal_laws.clear_laws_cache()
    return persist


def test_list_laws_from_index(laws_env: Path) -> None:
    page = legal_laws.list_laws(q="", offset=0, limit=10)
    assert page["total"] == 3
    assert page["items"][0]["law_id"] == "10"
    assert page["ingested_count"] == 0
    assert page["failed_count"] == 0
    assert page["remaining_count"] == 3

    found = legal_laws.list_laws(q="12701", offset=0, limit=10)
    assert found["total"] == 1
    assert found["items"][0]["title"].startswith("ШҮҮХИЙН")

    orphan = legal_laws.list_laws(q="999999", offset=0, limit=5)
    assert orphan["total"] == 1
    assert orphan["items"][0]["law_id"] == "999999"


def test_ingested_laws_disappear_from_list(laws_env: Path) -> None:
    legal_laws.mark_law_ingested("10", title="ӨРШӨӨЛ ҮЗҮҮЛЭХ ТУХАЙ")
    page = legal_laws.list_laws(q="", offset=0, limit=10)
    assert page["total"] == 2
    assert {row["law_id"] for row in page["items"]} == {"15", "12701"}
    assert page["ingested_count"] == 1
    assert page["remaining_count"] == 2

    gone = legal_laws.list_laws(q="10", offset=0, limit=5)
    assert gone["total"] == 0
    assert gone["items"] == []


def test_failed_laws_leave_queue_and_can_retry(laws_env: Path) -> None:
    legal_laws.mark_law_failed("15", title="ҮНЭТ ЦААС", error="текст олдсонгүй", reason="error")
    page = legal_laws.list_laws(q="", offset=0, limit=10)
    assert "15" not in {row["law_id"] for row in page["items"]}
    assert page["failed_count"] == 1
    assert page["remaining_count"] == 2

    failed = legal_laws.list_failed_laws()
    assert failed["count"] == 1
    assert failed["items"][0]["law_id"] == "15"
    assert "олдсонгүй" in failed["items"][0]["error"]

    assert legal_laws.clear_law_failed("15") is True
    back = legal_laws.list_laws(q="", offset=0, limit=10)
    assert "15" in {row["law_id"] for row in back["items"]}
    assert back["failed_count"] == 0


def test_skip_law_dismisses_without_fetch(laws_env: Path) -> None:
    row = legal_laws.skip_law("10", title="ӨРШӨӨЛ", note="гарын авлагын хасалт")
    assert row["reason"] == "skipped"
    page = legal_laws.list_laws(q="", offset=0, limit=10)
    assert "10" not in {row["law_id"] for row in page["items"]}


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
