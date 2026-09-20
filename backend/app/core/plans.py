"""Subscription plan catalog — free + two paid SKUs (QPay-ready)."""

from __future__ import annotations

from typing import Any

# Honest per-check ceiling measured on real legalinfo Civil Code text in the
# editor: ~100k completes; ~200k+ leaves the UI spinning. Cap below that.
PRACTICAL_CHECK_MAX_CHARS = 80_000

# Three user classes:
#   1) free — үнэгүй
#   2) pro_3m — 3 сар · ₮6,000
#   3) pro_year — 1 жил · ₮19,900
PLANS: dict[str, dict[str, Any]] = {
    "free": {
        "id": "free",
        "name": "Үнэгүй",
        "price_mnt": 0,
        "duration_days": None,
        "interval": "none",
        "check_max_chars": PRACTICAL_CHECK_MAX_CHARS,
        "checks_per_day": None,
        "features": ["Зөв бичих", "Монгол бичиг", "Нэг дор 80 мянган тэмдэгт"],
        "badge": "",
        "sort": 0,
    },
    "pro_3m": {
        "id": "pro_3m",
        "name": "3 сар",
        "price_mnt": 6_000,
        "duration_days": 90,
        "interval": "quarter",
        "check_max_chars": PRACTICAL_CHECK_MAX_CHARS,
        "checks_per_day": None,
        "features": [
            "Зөв бичих",
            "Монгол бичиг",
            "AI засах",
            "Нэг дор 80 мянган тэмдэгт",
            "Бүрэн эрх · 3 сар",
        ],
        "badge": "сард ₮2,000",
        "sort": 1,
    },
    "pro_year": {
        "id": "pro_year",
        "name": "1 жил",
        "price_mnt": 19_900,
        "duration_days": 365,
        "interval": "year",
        "check_max_chars": PRACTICAL_CHECK_MAX_CHARS,
        "checks_per_day": None,
        "features": [
            "Зөв бичих",
            "Монгол бичиг",
            "AI засах",
            "Нэг дор 80 мянган тэмдэгт",
            "Бүрэн эрх · 1 жил",
        ],
        "badge": "хамгийн ашигтай · сард ~₮1,658",
        "sort": 2,
    },
}

# Legacy id from earlier scaffolding — treat as annual.
_ALIASES = {"pro": "pro_year"}

DEFAULT_PLAN = "free"
PAID_PLAN_IDS = frozenset({"pro_3m", "pro_year", "pro"})


def normalize_plan_id(plan_id: str) -> str:
    raw = (plan_id or DEFAULT_PLAN).strip()
    return _ALIASES.get(raw, raw)


def list_plans(*, include_free: bool = True) -> list[dict[str, Any]]:
    keys = ("free", "pro_3m", "pro_year") if include_free else ("pro_3m", "pro_year")
    return [dict(PLANS[key]) for key in keys]


def list_paid_plans() -> list[dict[str, Any]]:
    return list_plans(include_free=False)


def get_plan(plan_id: str) -> dict[str, Any]:
    key = normalize_plan_id(plan_id)
    return dict(PLANS.get(key) or PLANS[DEFAULT_PLAN])


def is_paid_plan(plan_id: str) -> bool:
    return normalize_plan_id(plan_id) in {"pro_3m", "pro_year"}


def effective_check_max_chars(user: dict[str, Any] | None = None) -> int:
    """Guest and free users get the free-plan ceiling; paid users get theirs."""
    from app.core.config import settings

    hard_cap = min(int(settings.check_max_chars), PRACTICAL_CHECK_MAX_CHARS)
    if user:
        entitlements = user.get("entitlements") or {}
        raw = entitlements.get("check_max_chars")
        if raw is not None:
            try:
                return min(int(raw), hard_cap)
            except (TypeError, ValueError):
                pass
    return min(int(get_plan(DEFAULT_PLAN)["check_max_chars"]), hard_cap)
