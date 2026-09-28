"""Small HTMX lessons. The books table stays a later example, not these pages."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from app.auth.deps import require_user_html
from app.db import books as books_repo
from app.web.pages_routes import shell_ctx, templates

router = APIRouter()

# Only the tutorial card uses this wait. The books list does not.
MAX_DEMO_DELAY_SECONDS = 5.0


def _lesson_ctx(request: Request, user: dict, lesson: int, **extra) -> dict:
    ctx = shell_ctx(request, user, active="tutorial")
    ctx.update(lesson=lesson, **extra)
    return ctx


async def _first_book() -> dict | None:
    rows, _total = await books_repo.list_books(page=1, size=1, ordering="title")
    return rows[0] if rows else None


@router.get("/tutorial", response_class=HTMLResponse)
async def tutorial_home(
    request: Request,
    user: dict = Depends(require_user_html),
):
    return templates.TemplateResponse(
        request,
        "tutorial/index.html",
        _lesson_ctx(request, user, 0),
    )


@router.get("/tutorial/1", response_class=HTMLResponse)
async def lesson_link(
    request: Request,
    user: dict = Depends(require_user_html),
):
    return templates.TemplateResponse(
        request,
        "tutorial/lesson_1.html",
        _lesson_ctx(request, user, 1, book=await _first_book()),
    )


@router.get("/tutorial/2", response_class=HTMLResponse)
async def lesson_fetch(
    request: Request,
    user: dict = Depends(require_user_html),
):
    return templates.TemplateResponse(
        request,
        "tutorial/lesson_2.html",
        _lesson_ctx(request, user, 2, book=await _first_book()),
    )


@router.get("/tutorial/3", response_class=HTMLResponse)
async def lesson_indicator(
    request: Request,
    user: dict = Depends(require_user_html),
):
    return templates.TemplateResponse(
        request,
        "tutorial/lesson_3.html",
        _lesson_ctx(request, user, 3, book=await _first_book()),
    )


@router.get("/tutorial/books/{book_id}", response_class=HTMLResponse)
async def lesson_book_page(
    request: Request,
    book_id: str,
    user: dict = Depends(require_user_html),
):
    book = await books_repo.get_book(book_id)
    return templates.TemplateResponse(
        request,
        "tutorial/book_page.html",
        _lesson_ctx(request, user, 1, book=book),
        status_code=200 if book else 404,
    )


@router.get("/tutorial/books/{book_id}/card", response_class=HTMLResponse)
async def lesson_book_card(
    request: Request,
    book_id: str,
    _user: dict = Depends(require_user_html),
    delay: float = Query(
        0,
        ge=0,
        le=MAX_DEMO_DELAY_SECONDS,
        description="Artificial wait, in seconds, so the indicator lesson is visible.",
    ),
):
    """HTML fragment. A non-zero delay exists only so lesson 3 can show a spinner."""
    if delay:
        await asyncio.sleep(delay)
    book = await books_repo.get_book(book_id)
    return templates.TemplateResponse(
        request,
        "tutorial/book_card.html",
        {"book": book, "delay": delay},
        status_code=200 if book else 404,
    )
