"""Large-document check must finish (legal statutes repeat vocabulary)."""

from __future__ import annotations

import time

from app.engine.runtime import get_engine, run_engine_check


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
