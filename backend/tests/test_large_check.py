"""Large-document check must finish within the honest practical ceiling."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.plans import PRACTICAL_CHECK_MAX_CHARS
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
    text = (" ".join(typos) + " ") * 400
    assert len(text) > 50_000
    assert len(set(text.split())) == len(typos)

    t0 = time.perf_counter()
    corrections = run_engine_check(text, "government_official")
    elapsed = time.perf_counter() - t0

    assert elapsed < 15.0, f"large repeated check took {elapsed:.1f}s"
    assert corrections, "expected some spelling marks"
    assert len(corrections) <= 900


def test_diverse_typos_at_58k_finish_quickly() -> None:
    """Many unique misspellings near the practical ceiling must not hang."""
    get_engine()
    sample_path = Path("/tmp/irgenii_huuli.txt")
    if sample_path.is_file():
        raw = sample_path.read_text()[:58_000]
    else:
        unit = "Иргэний хуулийн дагуу гэрээ байгуулахдаа талууд эрх үүргээ тодорхой заана. "
        raw = (unit * 3_000)[:58_000]
    parts: list[str] = []
    for i, word in enumerate(raw.split()):
        if len(word) >= 5 and i % 3 == 0:
            parts.append(word[:-1] + "ы" + word[-1] if "ы" not in word else word + "г")
        else:
            parts.append(word)
    text = " ".join(parts)[:58_000]
    assert len(text) >= 50_000
    assert len(set(text.split())) > 1_500

    t0 = time.perf_counter()
    corrections = run_engine_check(text, "government_official")
    elapsed = time.perf_counter() - t0

    assert elapsed < 20.0, f"58k diverse check took {elapsed:.1f}s"
    assert isinstance(corrections, list)
    assert len(corrections) <= 900


def test_practical_ceiling_rejects_civil_code_size() -> None:
    """~460k Civil Code must fail fast — do not spin forever."""
    sample_path = Path("/tmp/irgenii_huuli.txt")
    if sample_path.is_file():
        text = sample_path.read_text()[:460_000]
    else:
        text = ("Иргэний хуулийн зүйл. " * 20_000)[:460_000]
    assert len(text) > PRACTICAL_CHECK_MAX_CHARS

    client = TestClient(app)
    t0 = time.perf_counter()
    response = client.post(
        "/api/v1/check/deterministic",
        json={"text": text, "document_type": "general", "style": "government_official"},
    )
    elapsed = time.perf_counter() - t0
    assert response.status_code == 413, response.text[:300]
    assert elapsed < 2.0, f"over-limit reject took {elapsed:.1f}s"


def test_practical_ceiling_accepts_80k_legal_sample() -> None:
    sample_path = Path("/tmp/irgenii_huuli.txt")
    if sample_path.is_file():
        text = sample_path.read_text()[:PRACTICAL_CHECK_MAX_CHARS]
    else:
        unit = "Иргэний хуулийн дагуу гэрээ байгуулахдаа талууд эрх үүргээ тодорхой заана. "
        text = (unit * 5_000)[:PRACTICAL_CHECK_MAX_CHARS]
    assert len(text) == PRACTICAL_CHECK_MAX_CHARS

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
    assert elapsed < 30.0, f"80k API check took {elapsed:.1f}s"
    assert isinstance(body["corrections"], list)
