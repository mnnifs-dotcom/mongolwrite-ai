"""Large-document check must finish (legal statutes repeat vocabulary)."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.engine.runtime import get_engine, run_engine_check
from app.main import app


def test_repeated_misspellings_finish_quickly() -> None:
    get_engine()
    bases = [
        "байгууллага",
        "хариуцагч",
        "нэхэмжлэгч",
        "гэрээ",
        "өмчлөх",
        "залгамжлал",
        "шүүх",
        "хууль",
    ]
    typos: list[str] = []
    for base in bases:
        typos.append(base[:-1] + base[-1] + base[-1])
        typos.append(base[:2] + "ы" + base[2:])
    # ~200k chars, only 16 unique misspellings — used to hang for minutes.
    text = (" ".join(typos) + " ") * 1200
    assert len(text) > 150_000
    assert len(set(text.split())) == len(typos)

    t0 = time.perf_counter()
    corrections = run_engine_check(text, "government_official")
    elapsed = time.perf_counter() - t0

    assert elapsed < 20.0, f"large repeated check took {elapsed:.1f}s"
    assert corrections, "expected some spelling marks"
    # Cap: do not return tens of thousands of duplicate marks.
    assert len(corrections) <= 900


def test_civil_code_sample_via_api() -> None:
    """Real legalinfo Civil Code excerpt must return 200 within a minute."""
    sample_path = Path("/tmp/irgenii_huuli.txt")
    if not sample_path.is_file():
        unit = (
            "Иргэний хуулийн дагуу гэрээ байгуулахдаа талууд эрх, үүргээ тодорхой заана. "
            "Хариуцагч нэхэмжлэгчийн шаардлагыг биелүүлээгүй бол шүүхэд хандаж болно. "
        )
        text = unit * 8_000
    else:
        text = sample_path.read_text()[:460_000]
    assert len(text) > 100_000

    client = TestClient(app)
    t0 = time.perf_counter()
    response = client.post(
        "/api/v1/check/deterministic",
        json={"text": text, "document_type": "general", "style": "government_official"},
    )
    elapsed = time.perf_counter() - t0
    assert response.status_code == 200, response.text[:300]
    body = response.json()
    assert body["character_count"] == len(text)
    assert elapsed < 60.0, f"civil-code API check took {elapsed:.1f}s"
    assert isinstance(body["corrections"], list)
