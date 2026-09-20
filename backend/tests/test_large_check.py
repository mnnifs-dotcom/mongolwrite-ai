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


def test_diverse_typos_at_large_sizes_finish_quickly() -> None:
    get_engine()
    for size in (80_000, 100_000, 300_000, 500_000):
        text = _diverse_legal_typos(size)
        assert len(text) == size
        t0 = time.perf_counter()
        corrections = run_engine_check(text, "government_official")
        elapsed = time.perf_counter() - t0
        # Typo-dense warm path is CPU-heavy; keep honest but allow headroom.
        limit = 6.0 if size >= 300_000 else 3.0
        assert elapsed < limit, f"{size} diverse check took {elapsed:.1f}s"
        assert isinstance(corrections, list)
        assert len(corrections) <= 900


def test_practical_ceiling_rejects_over_limit() -> None:
    """Text above the paid ceiling must fail fast — do not spin forever."""
    sample_path = Path("/tmp/irgenii_huuli.txt")
    over = PRACTICAL_CHECK_MAX_CHARS + 50_000
    if sample_path.is_file():
        text = sample_path.read_text()[:over]
    else:
        text = ("Иргэний хуулийн зүйл. " * 30_000)[:over]
    if len(text) <= PRACTICAL_CHECK_MAX_CHARS:
        text = (text + " " + text)[:over]
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


def test_practical_ceiling_accepts_500k_for_paid_user(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    from app.core.user_auth import set_user_cookie
    from app.core.users import activate_plan_for_user, upsert_google_user

    upsert_google_user(sub="paid500k", email="paid500k@example.com")
    activate_plan_for_user("paid500k", "pro_year")

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
    # Attach paid session cookie the same way the auth layer signs it.
    response_cookie = client.get("/api/v1/settings")
    assert response_cookie.status_code == 200
    from starlette.responses import Response

    probe = Response()
    set_user_cookie(probe, "paid500k")
    cookie_header = probe.headers.get("set-cookie", "")
    assert "mw_user=" in cookie_header
    token = cookie_header.split("mw_user=", 1)[1].split(";", 1)[0]
    client.cookies.set("mw_user", token)

    settings = client.get("/api/v1/settings")
    assert settings.json()["check_max_chars"] == PRACTICAL_CHECK_MAX_CHARS

    t0 = time.perf_counter()
    response = client.post(
        "/api/v1/check/deterministic",
        json={"text": text, "document_type": "general", "style": "government_official"},
    )
    elapsed = time.perf_counter() - t0
    assert response.status_code == 200, response.text[:300]
    body = response.json()
    assert body["character_count"] == len(text)
    assert elapsed < 5.0, f"500k API check took {elapsed:.1f}s"
    assert isinstance(body["corrections"], list)
