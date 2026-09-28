"""Small HTMX lessons. The books table stays a later example, not these pages."""

from __future__ import annotations

import asyncio
import json
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse

from app.auth.deps import require_editor_html, require_user_html, verify_csrf
from app.db import books as books_repo
from app.db.books import BOOK_CATEGORIES
from app.ui.books_routes import CATEGORY_LABELS
from app.ui.pages_routes import shell_ctx, templates

router = APIRouter()

# Only tutorial endpoints use these waits. The books list does not.
MAX_DEMO_DELAY_SECONDS = 5.0
# A one-letter search sleeps so an older response can arrive after a newer one.
SLOW_SHORT_QUERY_SECONDS = 1.2
LIST_LIMIT = 8
SHELF_SIZE = 5
SHELF_ORDERINGS = frozenset({"title", "author"})
PRACTICE_ISBN = "tutorial-practice"
PRACTICE_TITLE = "Practice shelf book"
PRACTICE_AUTHOR = "Tutorial"


def _lesson_ctx(request: Request, user: dict, lesson: int, **extra) -> dict:
    ctx = shell_ctx(request, user, active="tutorial")
    ctx.update(lesson=lesson, **extra)
    return ctx


async def _first_book() -> dict | None:
    rows, _total = await books_repo.list_books(page=1, size=1, ordering="title")
    return rows[0] if rows else None


def _parse_simple_book(
    title: str, author: str, year: str
) -> tuple[dict | None, str | None]:
    title = title.strip()
    author = author.strip()
    if not title or not author:
        return None, "Title and author are required."
    year_val: int | None = None
    if year.strip():
        try:
            year_val = int(year.strip())
        except ValueError:
            return None, "Year must be a number."
        if year_val < 0 or year_val > 9999:
            return None, "Year must be between 0 and 9999."
    return {"title": title, "author": author, "year": year_val}, None


async def _practice_book(user_id: int) -> dict:
    """The edit/delete lessons use one row, created again if it was removed."""
    rows, _total = await books_repo.list_books(
        page=1, size=20, q=PRACTICE_ISBN, ordering="title"
    )
    for row in rows:
        if row.get("isbn") == PRACTICE_ISBN:
            return row
    return await books_repo.create_book(
        PRACTICE_TITLE,
        PRACTICE_AUTHOR,
        category="other",
        isbn=PRACTICE_ISBN,
        notes="Practice row for the tutorial. The sample shelf does not use this ISBN.",
        added_by_user_id=user_id,
    )


def _wants_fragment(request: Request) -> bool:
    """A history restore must get the full page. A normal HTMX swap gets the shelf."""
    if request.headers.get("HX-History-Restore-Request") == "true":
        return False
    return request.headers.get("HX-Request") == "true"


def _shelf_url(page: int, ordering: str) -> str:
    return "/ui/tutorial/10?" + urlencode({"page": page, "ordering": ordering})


async def _shelf_data(page: int, ordering: str | None) -> dict:
    chosen = ordering if ordering in SHELF_ORDERINGS else "title"
    rows, total = await books_repo.list_books(
        page=page, size=SHELF_SIZE, ordering=chosen
    )
    pages = books_repo.total_pages(total, SHELF_SIZE)
    if pages and page > pages:
        page = pages
        rows, total = await books_repo.list_books(
            page=page, size=SHELF_SIZE, ordering=chosen
        )
    return {
        "books": rows,
        "page": page,
        "total": total,
        "total_pages": pages,
        "ordering": chosen,
        "prev_url": _shelf_url(page - 1, chosen) if page > 1 else None,
        "next_url": _shelf_url(page + 1, chosen) if pages and page < pages else None,
        "title_url": _shelf_url(1, "title"),
        "author_url": _shelf_url(1, "author"),
    }


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
    panel: str = Query(""),
):
    """HTML fragment. A non-zero delay exists only so lesson 3 can show a spinner."""
    if delay:
        await asyncio.sleep(delay)
    book = await books_repo.get_book(book_id)
    template = (
        "tutorial/practice_card.html" if panel == "practice" else "tutorial/book_card.html"
    )
    return templates.TemplateResponse(
        request,
        template,
        {"book": book, "delay": delay},
        status_code=200 if book else 404,
    )


@router.get("/tutorial/7", response_class=HTMLResponse)
async def lesson_add(
    request: Request,
    user: dict = Depends(require_user_html),
):
    return templates.TemplateResponse(
        request,
        "tutorial/lesson_7.html",
        _lesson_ctx(request, user, 7),
    )


@router.post(
    "/tutorial/books",
    response_class=HTMLResponse,
    dependencies=[Depends(verify_csrf)],
)
async def lesson_add_book(
    request: Request,
    _user: dict = Depends(require_editor_html),
    title: str = Form(""),
    author: str = Form(""),
    year: str = Form(""),
):
    payload, form_error = _parse_simple_book(title, author, year)
    if form_error or payload is None:
        return templates.TemplateResponse(
            request,
            "tutorial/form_error.html",
            {"message": form_error or "Title and author are required."},
            status_code=400,
        )
    book = await books_repo.create_book(
        payload["title"],
        payload["author"],
        year=payload["year"],
        category="other",
        added_by_user_id=_user["id"],
    )
    return templates.TemplateResponse(
        request,
        "tutorial/saved_card.html",
        {"book": book},
    )


@router.get("/tutorial/8", response_class=HTMLResponse)
async def lesson_edit(
    request: Request,
    user: dict = Depends(require_user_html),
):
    book = await _practice_book(user["id"])
    return templates.TemplateResponse(
        request,
        "tutorial/lesson_8.html",
        _lesson_ctx(request, user, 8, book=book),
    )


@router.get("/tutorial/books/{book_id}/edit", response_class=HTMLResponse)
async def lesson_edit_form(
    request: Request,
    book_id: str,
    user: dict = Depends(require_editor_html),
):
    book = await books_repo.get_book(book_id)
    if book is None:
        return HTMLResponse("That book is not in the catalog.", status_code=404)
    return templates.TemplateResponse(
        request,
        "tutorial/book_edit.html",
        {
            "book": book,
            "csrf_token": _lesson_ctx(request, user, 8)["csrf_token"],
            "message": None,
        },
    )


@router.put(
    "/tutorial/books/{book_id}",
    response_class=HTMLResponse,
    dependencies=[Depends(verify_csrf)],
)
async def lesson_update_book(
    request: Request,
    book_id: str,
    user: dict = Depends(require_editor_html),
    title: str = Form(""),
    author: str = Form(""),
):
    existing = await books_repo.get_book(book_id)
    if existing is None:
        return HTMLResponse("That book is not in the catalog.", status_code=404)
    payload, form_error = _parse_simple_book(title, author, "")
    csrf_token = _lesson_ctx(request, user, 8)["csrf_token"]
    if form_error or payload is None:
        draft = {**existing, "title": title, "author": author}
        return templates.TemplateResponse(
            request,
            "tutorial/book_edit.html",
            {"book": draft, "csrf_token": csrf_token, "message": form_error},
            status_code=400,
        )
    book = await books_repo.update_book(
        book_id,
        title=payload["title"],
        author=payload["author"],
    )
    return templates.TemplateResponse(
        request,
        "tutorial/practice_card.html",
        {"book": book, "csrf_token": csrf_token},
    )


@router.delete(
    "/tutorial/books/{book_id}",
    response_class=HTMLResponse,
    dependencies=[Depends(verify_csrf)],
)
async def lesson_delete_book(
    request: Request,
    book_id: str,
    _user: dict = Depends(require_editor_html),
):
    deleted = await books_repo.delete_book(book_id)
    return templates.TemplateResponse(
        request,
        "tutorial/deleted.html",
        {"deleted": deleted},
        status_code=200 if deleted else 404,
    )


@router.get("/tutorial/9", response_class=HTMLResponse)
async def lesson_toast(
    request: Request,
    user: dict = Depends(require_user_html),
):
    book = await _practice_book(user["id"])
    return templates.TemplateResponse(
        request,
        "tutorial/lesson_9.html",
        _lesson_ctx(request, user, 9, book=book),
    )


@router.post(
    "/tutorial/books/{book_id}/announce",
    response_class=HTMLResponse,
    dependencies=[Depends(verify_csrf)],
)
async def lesson_announce(
    book_id: str,
    _user: dict = Depends(require_editor_html),
):
    book = await books_repo.get_book(book_id)
    if book is None:
        return HTMLResponse("That book is not in the catalog.", status_code=404)
    response = HTMLResponse("")
    response.headers["HX-Trigger"] = json.dumps(
        {
            "showToast": {
                "message": "Noted this book. The message was not in the HTML.",
                "level": "ok",
            }
        }
    )
    return response


@router.get("/tutorial/10", response_class=HTMLResponse)
async def lesson_pages(
    request: Request,
    user: dict = Depends(require_user_html),
    page: int = Query(1, ge=1),
    ordering: str | None = Query(None),
):
    data = await _shelf_data(page, ordering)
    template = "tutorial/shelf.html" if _wants_fragment(request) else "tutorial/lesson_10.html"
    return templates.TemplateResponse(
        request,
        template,
        _lesson_ctx(request, user, 10, **data),
    )


@router.get("/tutorial/11", response_class=HTMLResponse)
async def lesson_table(
    request: Request,
    user: dict = Depends(require_user_html),
):
    return templates.TemplateResponse(
        request,
        "tutorial/lesson_11.html",
        _lesson_ctx(request, user, 11),
    )
