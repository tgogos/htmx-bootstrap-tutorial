"""Small HTMX lessons. The books table stays a later example, not these pages."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from app.auth.deps import require_user_html
from app.db import books as books_repo
from app.db.books import BOOK_CATEGORIES
from app.web.books_routes import CATEGORY_LABELS
from app.web.pages_routes import shell_ctx, templates

router = APIRouter()

# Only tutorial endpoints use these waits. The books list does not.
MAX_DEMO_DELAY_SECONDS = 5.0
# A one-letter search sleeps so an older response can arrive after a newer one.
SLOW_SHORT_QUERY_SECONDS = 1.2
LIST_LIMIT = 8


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


@router.get("/tutorial/4", response_class=HTMLResponse)
async def lesson_swap(
    request: Request,
    user: dict = Depends(require_user_html),
):
    return templates.TemplateResponse(
        request,
        "tutorial/lesson_4.html",
        _lesson_ctx(request, user, 4, book=await _first_book()),
    )


@router.get("/tutorial/5", response_class=HTMLResponse)
async def lesson_trigger(
    request: Request,
    user: dict = Depends(require_user_html),
):
    categories = [
        (key, CATEGORY_LABELS[key]) for key in sorted(BOOK_CATEGORIES)
    ]
    return templates.TemplateResponse(
        request,
        "tutorial/lesson_5.html",
        _lesson_ctx(request, user, 5, categories=categories),
    )


@router.get("/tutorial/6", response_class=HTMLResponse)
async def lesson_search(
    request: Request,
    user: dict = Depends(require_user_html),
):
    return templates.TemplateResponse(
        request,
        "tutorial/lesson_6.html",
        _lesson_ctx(request, user, 6),
    )


@router.get("/tutorial/books", response_class=HTMLResponse)
async def lesson_book_list(
    request: Request,
    _user: dict = Depends(require_user_html),
    category: str | None = Query(None),
    q: str | None = Query(None),
    slow: int = Query(
        0,
        ge=0,
        le=1,
        description="When 1, a one-letter search waits so lesson 6 can show a stale response.",
    ),
):
    """HTML fragment: a short title list. Not the books table."""
    chosen = (category or "").strip() or None
    query = (q or "").strip() or None
    delay = 0.0
    if slow and query is not None and len(query) <= 1:
        delay = SLOW_SHORT_QUERY_SECONDS
        await asyncio.sleep(delay)

    unknown_category = chosen is not None and chosen not in BOOK_CATEGORIES
    books: list[dict] = []
    total = 0
    if not unknown_category and (chosen or query):
        books, total = await books_repo.list_books(
            page=1,
            size=LIST_LIMIT,
            q=query,
            category=chosen,
            ordering="title",
        )

    return templates.TemplateResponse(
        request,
        "tutorial/book_list.html",
        {
            "books": books,
            "total": total,
            "q": query,
            "category_label": CATEGORY_LABELS.get(chosen) if chosen else None,
            "unknown_category": unknown_category,
            "delay": delay,
            "limited": total > LIST_LIMIT,
        },
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
