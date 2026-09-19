"""Subscription plan catalog — billing enforcement comes later."""

from __future__ import annotations

from typing import Any

# Soft prep for paid tiers. Free stays generous until checkout ships.
PLANS: dict[str, dict[str, Any]] = {
    "free": {
        "id": "free",
        "name": "Үнэгүй",
        "price_mnt": 0,
        "check_max_chars": 100_000,
        "checks_per_day": None,
        "features": ["Зөв бичих", "Монгол бичиг"],
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "price_mnt": 9_900,
        "check_max_chars": 100_000,
        "checks_per_day": None,
        "features": ["Зөв бичих", "Монгол бичиг", "AI засах", "Илүү их хэрэглээ"],
    },
}

DEFAULT_PLAN = "free"


def list_plans() -> list[dict[str, Any]]:
    return [dict(PLANS[key]) for key in ("free", "pro")]


def get_plan(plan_id: str) -> dict[str, Any]:
    return dict(PLANS.get(plan_id) or PLANS[DEFAULT_PLAN])
