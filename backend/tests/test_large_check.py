"""Large-document check must finish within the honest practical ceiling."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.plans import PRACTICAL_CHECK_MAX_CHARS
from app.engine.runtime import get_engine, run_engine_check
from app.main import app


def _diverse_legal_typos(size: int) -> str:
    sample_path = Path("/tmp/irgenii_huuli.txt")
    if sample_path.is_file():
        raw = sample_path.read_text()[:size]
    else:
        unit = "Иргэний хуулийн дагуу гэрээ байгуулахдаа талууд эрх үүргээ тодорхой заана. "
        raw = (unit * ((size // len(unit)) + 5))[:size]
    parts: list[str] = []
    for i, word in enumerate(raw.split()):
        if len(word) >= 5 and i % 2 == 0:
            parts.append(word[:-1] + "ы" + word[-1] if "ы" not in word else word + "г")
        elif len(word) >= 4 and i % 3 == 0:
            parts.append(word[:2] + "ө" + word[2:])
        else:
            parts.append(word)
    return " ".join(parts)[:size]


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

    assert elapsed < 3.0, f"large repeated check took {elapsed:.1f}s"
    assert corrections, "expected some spelling marks"
    assert len(corrections) <= 900


def test_diverse_typos_at_58k_finish_under_3s() -> None:
    """Many unique misspellings near 58k must finish in ~3s."""
    get_engine()
    text = _diverse_legal_typos(58_000)
    assert len(text) >= 50_000
    assert len(set(text.split())) > 1_500

    t0 = time.perf_counter()
    corrections = run_engine_check(text, "government_official")
    elapsed = time.perf_counter() - t0

    assert elapsed < 3.0, f"58k diverse check took {elapsed:.1f}s"
    assert isinstance(corrections, list)
    assert len(corrections) <= 900


def test_diverse_typos_at_80k_100k_300k_finish_under_3s() -> None:
    get_engine()
    for size in (80_000, 100_000, 300_000):
        text = _diverse_legal_typos(size)
        assert len(text) == size
        t0 = time.perf_counter()
        corrections = run_engine_check(text, "government_official")
        elapsed = time.perf_counter() - t0
        assert elapsed < 3.0, f"{size} diverse check took {elapsed:.1f}s"
        assert isinstance(corrections, list)
        assert len(corrections) <= 900


def test_practical_ceiling_rejects_over_300k() -> None:
    """Text above the 300k ceiling must fail fast — do not spin forever."""
    sample_path = Path("/tmp/irgenii_huuli.txt")
    if sample_path.is_file():
        text = sample_path.read_text()[:460_000]
    else:
        text = ("Иргэний хуулийн зүйл. " * 20_000)[:460_000]
    if len(text) <= PRACTICAL_CHECK_MAX_CHARS:
        text = (text + " " + text)[: PRACTICAL_CHECK_MAX_CHARS + 50_000]
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


def test_practical_ceiling_accepts_300k_legal_sample() -> None:
    sample_path = Path("/tmp/irgenii_huuli.txt")
    if sample_path.is_file():
        text = sample_path.read_text()[:PRACTICAL_CHECK_MAX_CHARS]
    else:
        unit = "Иргэний хуулийн дагуу гэрээ байгуулахдаа талууд эрх үүргээ тодорхой заана. "
        text = (unit * 20_000)[:PRACTICAL_CHECK_MAX_CHARS]
    if len(text) < PRACTICAL_CHECK_MAX_CHARS:
        text = (text + " " + text)[:PRACTICAL_CHECK_MAX_CHARS]
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
    assert elapsed < 3.0, f"300k API check took {elapsed:.1f}s"
    assert isinstance(body["corrections"], list)
