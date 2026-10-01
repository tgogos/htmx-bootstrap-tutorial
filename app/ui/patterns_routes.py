"""Patterns pages. A second sequence after lessons 1–13, still one idea per page.

These routes read and write the same books as /ui/books. The books table itself
does not gain checkboxes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.auth.deps import require_editor_html, require_user_html, verify_csrf
from app.auth.users import role_at_least
from app.db import books as books_repo
from app.ui.pages_routes import shell_ctx, templates

router = APIRouter()

PAGE_SIZE = 8
MAX_IDS = 50
EXPORT_STEPS = 4
_EXPORT_KEY = "pattern_export"


def _ctx(request: Request, user: dict, lesson: int, **extra) -> dict:
    ctx = shell_ctx(request, user, active="patterns")
    ctx.update(
        lesson=lesson,
        can_edit=role_at_least(user["role"], "editor"),
        **extra,
    )
    return ctx


def _clean_ids(book_ids: list[str] | None) -> list[str]:
    seen: list[str] = []
    for raw in book_ids or []:
        book_id = raw.strip()
        if book_id and book_id not in seen:
            seen.append(book_id)
        if len(seen) >= MAX_IDS:
            break
    return seen


async def _shelf() -> tuple[list[dict], int]:
    rows, _total = await books_repo.list_books(
        page=1, size=PAGE_SIZE, ordering="title"
    )
    available = sum(1 for row in rows if row["available"])
    return rows, available


def _board(
    request: Request,
    user: dict,
    lesson: int,
    rows: list[dict],
    available: int,
    *,
    notice: str | None = None,
    oob: bool = False,
):
    return templates.TemplateResponse(
        request,
        "patterns/board.html",
        _ctx(
            request,
            user,
            lesson,
            books=rows,
            available_count=available,
            notice=notice,
            oob=oob,
        ),
    )


@router.get("/patterns", response_class=HTMLResponse)
async def patterns_home(
    request: Request,
    user: dict = Depends(require_user_html),
):
    return templates.TemplateResponse(
        request,
        "patterns/index.html",
        _ctx(request, user, 0),
    )


@router.get("/patterns/4/table", response_class=HTMLResponse)
async def pattern_refresh(
    request: Request,
    user: dict = Depends(require_user_html),
):
    rows, available = await _shelf()
    return _board(request, user, 4, rows, available)


@router.get("/patterns/{lesson}", response_class=HTMLResponse)
async def pattern_page(
    request: Request,
    lesson: int,
    user: dict = Depends(require_user_html),
):
    if lesson < 1 or lesson > 6:
        raise HTTPException(status_code=404, detail="Unknown pattern")
    rows, available = await _shelf()
    return templates.TemplateResponse(
        request,
        f"patterns/lesson_{lesson}.html",
        _ctx(
            request,
            user,
            lesson,
            books=rows,
            available_count=available,
            notice=None,
            oob=False,
        ),
    )


@router.post("/patterns/{lesson}/mark", response_class=HTMLResponse)
async def pattern_mark(
    request: Request,
    lesson: int,
    user: dict = Depends(require_editor_html),
    book_id: list[str] = Form(default_factory=list),
    available: str = Form(""),
    _: None = Depends(verify_csrf),
):
    if lesson not in (2, 3, 4):
        raise HTTPException(status_code=404, detail="Unknown pattern")
    ids = _clean_ids(book_id)
    notice = None
    if available not in ("0", "1"):
        notice = "Choose Mark available or Mark unavailable."
    elif not ids:
        notice = "Select at least one book."
    else:
        await books_repo.set_books_available(ids, available == "1")
    rows, count = await _shelf()
    return _board(
        request,
        user,
        lesson,
        rows,
        count,
        notice=notice,
        oob=lesson == 3,
    )


@router.post("/patterns/5/delete", response_class=HTMLResponse)
async def pattern_delete(
    request: Request,
    user: dict = Depends(require_editor_html),
    book_id: list[str] = Form(default_factory=list),
    _: None = Depends(verify_csrf),
):
    ids = _clean_ids(book_id)
    notice = None
    if not ids:
        notice = "Select at least one book."
    else:
        await books_repo.delete_books(ids)
    rows, count = await _shelf()
    return _board(request, user, 5, rows, count, notice=notice, oob=True)


def _export_percent(step: int) -> int:
    return int(step * 100 / EXPORT_STEPS)


def _job_response(
    request: Request,
    user: dict,
    *,
    step: int,
    titles: list[str],
    done: bool,
    idle: bool = False,
):
    return templates.TemplateResponse(
        request,
        "patterns/export_job.html",
        _ctx(
            request,
            user,
            6,
            step=step,
            percent=_export_percent(step),
            titles=titles,
            done=done,
            idle=idle,
        ),
    )


@router.post("/patterns/6/export", response_class=HTMLResponse)
async def pattern_export_start(
    request: Request,
    user: dict = Depends(require_editor_html),
    book_id: list[str] = Form(default_factory=list),
    _: None = Depends(verify_csrf),
):
    ids = _clean_ids(book_id)
    if not ids:
        return _job_response(request, user, step=0, titles=[], done=True)
    rows, _available = await _shelf()
    by_id = {row["id"]: row["title"] for row in rows}
    titles = [by_id[book_id] for book_id in ids if book_id in by_id]
    if not titles:
        return _job_response(request, user, step=0, titles=[], done=True)
    request.session[_EXPORT_KEY] = {"step": 0, "titles": titles}
    return _job_response(request, user, step=0, titles=titles, done=False)


@router.get("/patterns/6/export", response_class=HTMLResponse)
async def pattern_export_poll(
    request: Request,
    user: dict = Depends(require_user_html),
):
    job = request.session.get(_EXPORT_KEY)
    if not job:
        return _job_response(
            request, user, step=EXPORT_STEPS, titles=[], done=True, idle=True
        )
    step = int(job.get("step", 0)) + 1
    titles = list(job.get("titles") or [])
    done = step >= EXPORT_STEPS
    if done:
        request.session.pop(_EXPORT_KEY, None)
    else:
        request.session[_EXPORT_KEY] = {"step": step, "titles": titles}
    return _job_response(request, user, step=min(step, EXPORT_STEPS), titles=titles, done=done)
