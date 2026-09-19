from __future__ import annotations

from app.core.plans import get_plan, list_plans
from app.core.users import public_user, upsert_google_user


def test_plans_catalog() -> None:
    plans = list_plans()
    assert {row["id"] for row in plans} == {"free", "pro"}
    assert get_plan("pro")["price_mnt"] == 9_900


def test_upsert_google_user(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    first = upsert_google_user(sub="abc", email="a@example.com", name="A", picture="")
    assert first["plan"] == "free"
    second = upsert_google_user(sub="abc", email="a@example.com", name="A2", picture="")
    assert second["name"] == "A2"
    pub = public_user(second)
    assert pub["email"] == "a@example.com"
    assert pub["entitlements"]["check_max_chars"] > 0
