from __future__ import annotations

import re
from typing import Annotated, Any, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.core.auth import (
    clear_session_cookie,
    credentials_ok,
    production_admin_misconfigured,
    require_admin,
    set_session_cookie,
)
from app.core.config import settings
from app.core.devices import clear_devices, list_devices
from app.core.feedback import list_feedback
from app.core.plans import get_plan, list_plans
from app.core.users import list_users, set_user_plan

from app.engine.admin_review import collect_review_words, confirm_review, preview_keep_drop
from app.engine.hunspell_candidates import (
    admin_lists_payload,
    approve_words,
    counts,
    forget_admin_added,
    list_admin_added,
    list_candidates,
    queue_doubt_words,
    record_admin_added,
    record_from_text,
    reject_words,
)
from app.engine.learn import learn_accepted_words
from app.engine.legal_bot import bot_status
from app.engine.legal_import import apply_legal_lexicon, legal_import_preview
from app.engine.legal_laws import (
    clear_law_failed,
    ingest_law,
    list_failed_laws,
    list_laws,
    skip_law,
)
from app.engine.metrics import snapshot
from app.engine.pending import list_pending, pop_pending, pop_pending_many
from app.engine.runtime import get_engine

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
AdminDep = Annotated[None, Depends(require_admin)]


class LoginRequest(BaseModel):
    username: str = Field(default="", max_length=80)
    password: str = Field(default="", max_length=200)


class WordsAction(BaseModel):
    words: list[str] = Field(default_factory=list, max_length=2000)


class WordAction(BaseModel):
    word: str = Field(min_length=1, max_length=80)


class HarvestRequest(BaseModel):
    text: str = Field(default="", max_length=1_000_000)


class IngestRequest(BaseModel):
    text: str = Field(default="", max_length=1_000_000)


class LexiconRemoveRequest(BaseModel):
    words: list[str] = Field(default_factory=list, max_length=500)
    queue_as_doubt: bool = True


class UserPlanUpdate(BaseModel):
    plan: Literal["free", "pro_3m", "pro_year", "pro"] = "free"
    plan_expires_at: str | None = Field(default=None, max_length=40)


@router.post("/login")
def login(body: LoginRequest, response: Response) -> dict[str, bool]:
    if production_admin_misconfigured() or not settings.admin_password:
        raise HTTPException(
            status_code=503,
            detail="Админ нэвтрэлт тохируулаагүй (нууц үг / secret солиогүй)",
        )
    if not credentials_ok(body.username, body.password):
        raise HTTPException(status_code=401, detail="Нэвтрэх нэр эсвэл нууц үг буруу")
    set_session_cookie(response)
    return {"ok": True}


@router.post("/logout")
def logout(response: Response) -> dict[str, bool]:
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me")
def me(_: AdminDep) -> dict[str, str]:
    return {"role": "admin", "username": settings.admin_username}


@router.get("/overview")
def overview(_: AdminDep) -> dict[str, Any]:
    engine = get_engine()
    lists = admin_lists_payload()
    health = snapshot()
    pending = list_pending()
    return {
        "lexicon": {
            "seed": engine.dictionary.curated_lemma_count
            if hasattr(engine.dictionary, "curated_lemma_count")
            else len({w.casefold() for w in engine.dictionary._seed}),
            "has_hunspell": engine.dictionary.has_hunspell,
            "hunspell_stems": getattr(engine.dictionary, "hunspell_stem_count", 0),
            "admin_added": lists["counts"]["added"],
        },
        "pending_skipped": pending,
        "pending_count": len(pending),
        "candidates": {
            "reliable": lists["counts"]["reliable"],
            "doubt": lists["counts"]["doubt"],
            "total": lists["counts"]["total"],
            "reliable_items": lists["reliable"],
            "doubt_items": lists["doubt"],
        },
        "added_words": lists["added"],
        "health": health,
        "admin_username": settings.admin_username,
        "check_max_chars": settings.check_max_chars,
    }


@router.get("/health")
def site_health(_: AdminDep) -> dict[str, Any]:
    return snapshot()


@router.get("/pending")
def pending(_: AdminDep) -> dict[str, Any]:
    items = list_pending()
    return {"items": items, "count": len(items)}


@router.post("/pending/approve")
def pending_approve(body: WordAction, _: AdminDep) -> dict[str, Any]:
    item = pop_pending(body.word)
    if item is None:
        raise HTTPException(status_code=404, detail="Энэ үг хүлээгдэж байхгүй")
    dictionary = get_engine().dictionary
    added = dictionary.add_words([item["word"]])
    if not added:
        added = dictionary.ensure_curated([item["word"]])
    record_admin_added([item["word"]], source="pending")
    return {"added": added, "added_count": len(added), "word": item["word"]}


@router.post("/pending/approve-many")
def pending_approve_many(body: WordsAction, _: AdminDep) -> dict[str, Any]:
    if not body.words:
        raise HTTPException(status_code=400, detail="Үг сонгоогүй")
    popped = pop_pending_many(body.words)
    if not popped:
        raise HTTPException(status_code=404, detail="Сонгосон үг олдсонгүй")
    dictionary = get_engine().dictionary
    surface = [str(item["word"]) for item in popped]
    added = dictionary.add_words(surface)
    if len(added) < len(surface):
        ensured = dictionary.ensure_curated(surface)
        added = sorted({*added, *ensured})
    record_admin_added(surface, source="pending")
    return {
        "added": added,
        "added_count": len(added),
        "removed_count": len(popped),
        "words": surface,
    }


@router.post("/pending/reject")
def pending_reject(body: WordAction, _: AdminDep) -> dict[str, str]:
    item = pop_pending(body.word)
    if item is None:
        raise HTTPException(status_code=404, detail="Энэ үг хүлээгдэж байхгүй")
    return {"word": item["word"]}


@router.post("/pending/reject-many")
def pending_reject_many(body: WordsAction, _: AdminDep) -> dict[str, Any]:
    if not body.words:
        raise HTTPException(status_code=400, detail="Үг сонгоогүй")
    popped = pop_pending_many(body.words)
    return {
        "removed": [str(item["word"]) for item in popped],
        "removed_count": len(popped),
    }


@router.post("/ingest")
def ingest(body: IngestRequest, _: AdminDep) -> dict[str, Any]:
    """Queue checker-accepted words for review — does not write the lexicon."""
    queued = learn_accepted_words(get_engine(), body.text)
    return {
        "added": [],
        "added_count": 0,
        "queued": queued,
        "queued_count": len(queued),
    }


@router.get("/added-words")
def added_words(
    _: AdminDep,
    since: str = "",
    until: str = "",
    q: str = "",
) -> dict[str, Any]:
    items = list_admin_added(since=since, until=until, q=q)
    return {"items": items, "count": len(items)}


@router.get("/feedback")
def feedback_list(_: AdminDep, limit: int = 200) -> dict[str, Any]:
    """User error reports from «Алдаа мэдэгдэх»."""
    items = list_feedback(limit=limit)
    return {"items": items, "count": len(items)}


@router.get("/candidates")
def candidates(
    _: AdminDep,
    tier: Literal["reliable", "doubt", ""] = "",
) -> dict[str, Any]:
    items = list_candidates(tier or None)
    return {"items": items, "count": len(items), "counts": counts()}


@router.post("/candidates/approve")
def candidates_approve(body: WordsAction, _: AdminDep) -> dict[str, Any]:
    if not body.words:
        raise HTTPException(status_code=400, detail="Үг сонгоогүй")
    result = approve_words(get_engine(), body.words)
    return {**result, "counts": counts()}


@router.post("/candidates/reject")
def candidates_reject(body: WordsAction, _: AdminDep) -> dict[str, Any]:
    if not body.words:
        raise HTTPException(status_code=400, detail="Үг сонгоогүй")
    result = reject_words(body.words)
    return {**result, "counts": counts()}


@router.post("/candidates/harvest")
def candidates_harvest(body: HarvestRequest, _: AdminDep) -> dict[str, Any]:
    queued = record_from_text(get_engine(), body.text)
    return {"queued": queued, "counts": counts()}


@router.get("/lexicon/legal-preview")
def lexicon_legal_preview(_: AdminDep) -> dict[str, Any]:
    return legal_import_preview()


@router.post("/lexicon/legal-import")
def lexicon_legal_import(_: AdminDep) -> dict[str, Any]:
    """Queue legalinfo trusted + doubt lemmas for admin review (no lexicon write)."""
    result = apply_legal_lexicon(get_engine())
    return {**result, "counts": counts(), "preview": legal_import_preview()}


@router.get("/legal/laws")
def legal_laws(
    _: AdminDep,
    q: str = "",
    offset: int = 0,
    limit: int = 50,
    titled_only: bool = False,
) -> dict[str, Any]:
    """Paginated list of legalinfo.mn law links (from shipped sitemap index)."""
    return list_laws(q=q, offset=offset, limit=limit, titled_only=titled_only)


@router.get("/legal/laws/failed")
def legal_laws_failed(_: AdminDep, limit: int = 100) -> dict[str, Any]:
    return list_failed_laws(limit=limit)


@router.post("/legal/laws/{law_id}/ingest")
def legal_law_ingest(law_id: str, _: AdminDep) -> dict[str, Any]:
    """Fetch one law from legalinfo.mn, check it, add accepted words to the lexicon.

    Broken pages are marked failed and removed from the pending queue so they
    do not block the admin list forever.
    """
    if not re.fullmatch(r"\d{1,16}", law_id.strip()):
        raise HTTPException(status_code=400, detail="Буруу lawId")
    try:
        result = ingest_law(get_engine(), law_id.strip(), source="legal_law")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"legalinfo холбогдсонгүй: {exc}") from exc
    return {**result, "counts": counts()}


@router.post("/legal/laws/{law_id}/skip")
def legal_law_skip(law_id: str, _: AdminDep) -> dict[str, Any]:
    """Dismiss a broken/unwanted law from the pending queue without fetching."""
    if not re.fullmatch(r"\d{1,16}", law_id.strip()):
        raise HTTPException(status_code=400, detail="Буруу lawId")
    row = skip_law(law_id.strip(), note="Админ жагсаалтаас хассан")
    return {"skipped": row, "laws": list_laws(offset=0, limit=1)}


@router.post("/legal/laws/{law_id}/retry")
def legal_law_retry(law_id: str, _: AdminDep) -> dict[str, Any]:
    """Clear a failed/skipped mark so the law reappears in the pending queue."""
    if not re.fullmatch(r"\d{1,16}", law_id.strip()):
        raise HTTPException(status_code=400, detail="Буруу lawId")
    cleared = clear_law_failed(law_id.strip())
    if not cleared:
        raise HTTPException(status_code=404, detail="Алдаатай жагсаалтад олдсонгүй")
    return {"retried": law_id.strip(), "failed": list_failed_laws()}


@router.get("/legal/bot")
def legal_bot_status(_: AdminDep) -> dict[str, Any]:
    return bot_status()


class ReviewPreviewRequest(BaseModel):
    batch_words: list[str] = Field(default_factory=list, max_length=20_000)
    approved_text: str = Field(default="", max_length=2_000_000)


class ReviewConfirmRequest(BaseModel):
    keep: list[str] = Field(default_factory=list, max_length=20_000)
    remove_from_lexicon: list[str] = Field(default_factory=list, max_length=20_000)
    do_not_add: list[str] = Field(default_factory=list, max_length=20_000)


@router.get("/review")
def review_words(
    _: AdminDep,
    since: str = "",
    until: str = "",
    q: str = "",
) -> dict[str, Any]:
    """Unified word list for a date range (pending, hunspell, legal, added)."""
    return collect_review_words(since=since, until=until, q=q)


@router.post("/review/preview")
def review_preview(body: ReviewPreviewRequest, _: AdminDep) -> dict[str, Any]:
    return preview_keep_drop(
        batch_words=body.batch_words,
        approved_text=body.approved_text,
        dictionary=get_engine().dictionary,
    )


@router.post("/review/confirm")
def review_confirm(body: ReviewConfirmRequest, _: AdminDep) -> dict[str, Any]:
    result = confirm_review(
        get_engine(),
        keep=body.keep,
        remove_from_lexicon=body.remove_from_lexicon,
        do_not_add=body.do_not_add,
    )
    return {**result, "counts": counts()}


@router.get("/lexicon/words")
def lexicon_words(
    _: AdminDep,
    q: str = "",
    letter: str = "",
    offset: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    dictionary = get_engine().dictionary
    return dictionary.list_lexicon(query=q, letter=letter, offset=offset, limit=limit)


@router.get("/lexicon/export")
def lexicon_export(_: AdminDep) -> dict[str, Any]:
    """Full curated lexicon as one list (for copy / offline review)."""
    words = get_engine().dictionary.curated_lemmas()
    return {"words": words, "count": len(words)}


@router.post("/lexicon/remove")
def lexicon_remove(body: LexiconRemoveRequest, _: AdminDep) -> dict[str, Any]:
    if not body.words:
        raise HTTPException(status_code=400, detail="Үг сонгоогүй")
    dictionary = get_engine().dictionary
    removed = dictionary.remove_words(body.words)
    if removed:
        forget_admin_added(removed)
    queued: list[str] = []
    if body.queue_as_doubt and removed:
        queued = queue_doubt_words(removed)["queued"]
    return {
        "removed": removed,
        "removed_count": len(removed),
        "queued_as_doubt": queued,
        "queued_count": len(queued),
        "lexicon_total": dictionary.curated_lemma_count,
        "counts": counts(),
    }


@router.get("/users")
def admin_users(
    _: AdminDep,
    q: str = "",
    plan: str = "",
    offset: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    return list_users(q=q, plan=plan, offset=offset, limit=limit)


@router.get("/users/plans")
def admin_user_plans(_: AdminDep) -> dict[str, Any]:
    return {"plans": list_plans()}


@router.patch("/users/{user_id}/plan")
def admin_user_set_plan(user_id: str, body: UserPlanUpdate, _: AdminDep) -> dict[str, Any]:
    if not user_id.strip():
        raise HTTPException(status_code=400, detail="Хэрэглэгч олдсонгүй")
    plan = get_plan(body.plan)
    try:
        row = set_user_plan(
            user_id,
            plan["id"],
            plan_expires_at=body.plan_expires_at,
            auto_duration=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail="Хэрэглэгч олдсонгүй")
    from app.core.users import admin_user

    return {"ok": True, "user": admin_user(row)}


@router.get("/users/{user_id}/devices")
def admin_user_devices(user_id: str, _: AdminDep) -> dict[str, Any]:
    if not user_id.strip():
        raise HTTPException(status_code=400, detail="Хэрэглэгч олдсонгүй")
    from app.core.users import get_user

    if not get_user(user_id):
        raise HTTPException(status_code=404, detail="Хэрэглэгч олдсонгүй")
    devices = list_devices(user_id)
    return {"items": devices, "count": len(devices), "max": 2}


@router.post("/users/{user_id}/devices/clear")
def admin_user_clear_devices(user_id: str, _: AdminDep) -> dict[str, Any]:
    if not user_id.strip():
        raise HTTPException(status_code=400, detail="Хэрэглэгч олдсонгүй")
    row = clear_devices(user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Хэрэглэгч олдсонгүй")
    from app.core.users import admin_user

    return {"ok": True, "user": admin_user(row)}
