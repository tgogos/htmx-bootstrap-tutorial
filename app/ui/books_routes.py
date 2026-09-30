"""HTML / HTMX routes for books UI and admin users."""

from __future__ import annotations

import json
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth.deps import (
    get_or_create_csrf_token,
    require_admin_html,
    require_editor_html,
    require_user_html,
    verify_csrf,
)
from app.auth.users import (
    ROLES,
    count_admins,
    list_users,
    normalize_role,
    role_at_least,
    set_user_role,
)
from app.db import books as books_repo
from app.db.books import BOOK_CATEGORIES, normalize_category
from app.ui.pages_routes import render_not_found
from app.ui.pagination import DEFAULT_PAGE_SIZE, PAGE_SIZES, page_size, sort_column_state
from app.ui.paths import TEMPLATES_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["sort_column_state"] = sort_column_state

SORT_COLUMNS = (
    "title",
    "author",
    "category",
    "year",
    "page_count",
    "available",
    "added_by",
)

CATEGORY_LABELS: dict[str, str] = {
    "fiction": "Fiction",
    "nonfiction": "Nonfiction",
    "scifi": "Sci-Fi",
    "fantasy": "Fantasy",
    "mystery": "Mystery",
    "biography": "Biography",
    "other": "Other",
}
CATEGORY_CHOICES: list[tuple[str, str]] = [
    (key, CATEGORY_LABELS[key]) for key in sorted(BOOK_CATEGORIES)
]


def _wants_books_partial(request: Request) -> bool:
    """HTMX 4 refetches on Back/Forward and sends HX-Request with that refetch.

    A history restore must get the full page. A normal swap still gets the table fragment.
    """
    if request.headers.get("HX-History-Restore-Request") == "true":
        return False
    return request.headers.get("HX-Request") == "true"


def _can_edit(user: dict) -> bool:
    return role_at_least(user["role"], "editor")


def _ctx(request: Request, user: dict, **extra):
    ctx = {
        "request": request,
        "user": user,
        "csrf_token": get_or_create_csrf_token(request),
        "can_edit": _can_edit(user),
        "is_admin": role_at_least(user["role"], "admin"),
        "categories": CATEGORY_CHOICES,
        "category_labels": CATEGORY_LABELS,
        "active": "books",
        "nav_group": None,
        "extra_css": [],
        "extra_js": [],
        "main_class": "",
    }
    ctx.update(extra)
    if not _wants_books_partial(request):
        ctx["toast"] = request.session.pop("toast", None)
    return ctx


def _remember_toast(request: Request, message: str) -> None:
    request.session["toast"] = {"message": message, "level": "ok"}


def _parse_optional_int(raw: str | None) -> int | None:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    return int(raw)


def _parse_available_form(raw: str | None) -> bool | None:
    if raw is None or raw == "" or raw == "any":
        return None
    if raw in {"1", "true", "yes"}:
        return True
    if raw in {"0", "false", "no"}:
        return False
    return None


def _toggle_order(current: str, column: str) -> str:
    if current == column:
        return f"-{column}"
    return column


def _list_params(
    *,
    page: int,
    size: int,
    ordering: str,
    q: str | None = None,
    category: str | None = None,
    available: str | None = None,
    added_by_user_id: int | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
) -> dict[str, str | int]:
    params: dict[str, str | int] = {
        "page": page,
        "size": size,
        "ordering": ordering,
    }
    if q:
        params["q"] = q
    if category:
        params["category"] = category
    if available and available != "any":
        params["available"] = available
    if added_by_user_id is not None:
        params["added_by_user_id"] = added_by_user_id
    if year_min is not None:
        params["year_min"] = year_min
    if year_max is not None:
        params["year_max"] = year_max
    return params


def _books_list_url(
    base: str,
    *,
    page: int,
    size: int,
    ordering: str,
    q: str | None = None,
    category: str | None = None,
    available: str | None = None,
    added_by_user_id: int | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
) -> str:
    return f"{base}?{urlencode(_list_params(
        page=page,
        size=size,
        ordering=ordering,
        q=q,
        category=category,
        available=available,
        added_by_user_id=added_by_user_id,
        year_min=year_min,
        year_max=year_max,
    ))}"


_LIST_QUERY_KEYS = (
    "page",
    "size",
    "ordering",
    "q",
    "category",
    "available",
    "added_by_user_id",
    "year_min",
    "year_max",
    "return_to",
)


def _has_list_query(request: Request) -> bool:
    return any(key in request.query_params for key in _LIST_QUERY_KEYS)


def _list_return(
    *,
    page: int,
    size: int,
    ordering: str | None,
    q: str | None,
    category: str | None,
    available: str | None,
    added_by_user_id: int | None,
    year_min: int | None,
    year_max: int | None,
    return_to: str,
) -> tuple[str, str, str]:
    """List URL, the query string that reproduces it, and the sidebar key.

    return_to is list or search. It is not part of the list URL.
    """
    ordering_value = books_repo.normalize_ordering(ordering)
    size_value = page_size(size)
    cat = category if category in BOOK_CATEGORIES else None
    q_value = q.strip() if q and q.strip() else None
    dest = "search" if return_to == "search" else "list"
    base = "/ui/books/search" if dest == "search" else "/ui/books"
    params = _list_params(
        page=page,
        size=size_value,
        ordering=ordering_value,
        q=q_value,
        category=cat,
        available=available,
        added_by_user_id=added_by_user_id,
        year_min=year_min,
        year_max=year_max,
    )
    carry = {**params, "return_to": dest}
    active = "books-search" if dest == "search" else "books"
    return _books_list_url(base, **params), urlencode(carry), active  # type: ignore[arg-type]


def _plain_list(
    *,
    page: int,
    size: int,
    ordering: str,
    q: str | None,
    category: str | None,
    available: str | None,
    added_by_user_id: int | None,
    year_min: int | None,
    year_max: int | None,
    return_to: str,
) -> bool:
    return (
        return_to != "search"
        and page == 1
        and size == DEFAULT_PAGE_SIZE
        and ordering == books_repo.DEFAULT_ORDERING
        and not q
        and not category
        and not (available and available != "any")
        and added_by_user_id is None
        and year_min is None
        and year_max is None
    )


def _list_place(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=100),
    ordering: str | None = Query(None),
    q: str | None = Query(None),
    category: str | None = Query(None),
    available: str | None = Query(None),
    added_by_user_id: int | None = Query(None),
    year_min: int | None = Query(None),
    year_max: int | None = Query(None),
    return_to: str = Query("list"),
) -> dict[str, str]:
    """FastAPI dependency: where a book page should send the reader back."""
    if not _has_list_query(request):
        return {"list_href": "/ui/books", "carry_query": "", "active": "books"}
    list_href, carry_query, active = _list_return(
        page=page,
        size=size,
        ordering=ordering,
        q=q,
        category=category,
        available=available,
        added_by_user_id=added_by_user_id,
        year_min=year_min,
        year_max=year_max,
        return_to=return_to,
    )
    return {"list_href": list_href, "carry_query": carry_query, "active": active}


def _book_page_urls(book_id: str, place: dict[str, str]) -> dict[str, str]:
    carry = place["carry_query"]
    suffix = f"?{carry}" if carry else ""
    delete_href = f"/ui/books/{book_id}?redirect=1"
    if carry:
        delete_href = f"{delete_href}&{carry}"
    return {
        "list_href": place["list_href"],
        "carry_query": carry,
        "detail_href": f"/ui/books/{book_id}{suffix}",
        "edit_href": f"/ui/books/{book_id}/edit{suffix}",
        "delete_href": delete_href,
        "active": place["active"],
    }


def _active_filter_chips(
    *,
    q: str | None,
    category: str | None,
    available: str | None,
    added_by_label: str | None,
    year_min: int | None,
    year_max: int | None,
) -> list[str]:
    chips: list[str] = []
    if q:
        chips.append(f"Text: {q}")
    if category and category in CATEGORY_LABELS:
        chips.append(CATEGORY_LABELS[category])
    avail = _parse_available_form(available)
    if avail is True:
        chips.append("Available")
    elif avail is False:
        chips.append("Unavailable")
    if added_by_label:
        chips.append(f"Added by {added_by_label}")
    if year_min is not None and year_max is not None:
        chips.append(f"{year_min}–{year_max}")
    elif year_min is not None:
        chips.append(f"From {year_min}")
    elif year_max is not None:
        chips.append(f"Through {year_max}")
    return chips


async def _books_page_data(
    *,
    base_path: str,
    page: int,
    size: int,
    ordering: str | None = None,
    q: str | None = None,
    category: str | None = None,
    available: str | None = None,
    added_by_user_id: int | None = None,
    added_by_label: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
) -> dict:
    size = page_size(size)
    ordering = books_repo.normalize_ordering(ordering)
    avail = _parse_available_form(available)
    cat = category if category in BOOK_CATEGORIES else None

    async def _load(page_num: int) -> tuple[list, int, int]:
        rows, total = await books_repo.list_books(
            page=page_num,
            size=size,
            q=q,
            category=cat,
            available=avail,
            added_by_user_id=added_by_user_id,
            year_min=year_min,
            year_max=year_max,
            ordering=ordering,
        )
        pages = books_repo.total_pages(total, size)
        return rows, total, pages

    rows, total, pages = await _load(page)
    if pages and page > pages:
        page = pages
        rows, total, pages = await _load(page)

    def href(**overrides: object) -> str:
        kwargs = {
            "page": page,
            "size": size,
            "ordering": ordering,
            "q": q,
            "category": cat,
            "available": available,
            "added_by_user_id": added_by_user_id,
            "year_min": year_min,
            "year_max": year_max,
        }
        kwargs.update(overrides)
        return _books_list_url(base_path, **kwargs)  # type: ignore[arg-type]

    return_to = "search" if base_path.rstrip("/").endswith("/search") else "list"
    results_params: dict[str, str | int] = {
        **_list_params(
            page=page,
            size=size,
            ordering=ordering,
            q=q,
            category=cat,
            available=available,
            added_by_user_id=added_by_user_id,
            year_min=year_min,
            year_max=year_max,
        ),
        "return_to": return_to,
    }
    carry_query = ""
    if not _plain_list(
        page=page,
        size=size,
        ordering=ordering,
        q=q,
        category=cat,
        available=available,
        added_by_user_id=added_by_user_id,
        year_min=year_min,
        year_max=year_max,
        return_to=return_to,
    ):
        carry_query = urlencode(results_params)

    chips = _active_filter_chips(
        q=q,
        category=cat,
        available=available,
        added_by_label=added_by_label,
        year_min=year_min,
        year_max=year_max,
    )
    return {
        "books": rows,
        "total": total,
        "page": page,
        "size": size,
        "page_sizes": PAGE_SIZES,
        "total_pages": pages,
        "ordering": ordering,
        "sort_urls": {
            col: href(page=1, ordering=_toggle_order(ordering, col))
            for col in SORT_COLUMNS
        },
        "size_urls": {n: href(page=1, size=n) for n in PAGE_SIZES},
        "q": q or "",
        "category": cat or "",
        "available": available or "any",
        "added_by_user_id": added_by_user_id,
        "year_min": year_min if year_min is not None else "",
        "year_max": year_max if year_max is not None else "",
        "list_base": base_path,
        "results_query": urlencode(results_params),
        "carry_query": carry_query,
        "active_filters": chips,
        "show_filter_summary": base_path.rstrip("/").endswith("/search"),
        "first_url": href(page=1) if page > 1 else None,
        "prev_url": href(page=page - 1) if page > 1 else None,
        "next_url": href(page=page + 1) if pages and page < pages else None,
        "last_url": href(page=pages) if pages and page < pages else None,
    }


def _parse_book_form(
    *,
    title: str,
    author: str,
    year: str,
    notes: str,
    category: str,
    isbn: str,
    page_count: str,
    available: str | None,
) -> tuple[dict | None, str | None]:
    title = title.strip()
    author = author.strip()
    notes_val = notes.strip() or None
    isbn_val = isbn.strip() or None
    category_val = normalize_category(category.strip() if category else None)
    year_val: int | None = None
    pages_val: int | None = None
    available_val = available in {"1", "true", "on", "yes"}

    if not title or not author:
        return None, "Title and author are required."
    if year.strip():
        try:
            year_val = int(year.strip())
            if year_val < 0 or year_val > 9999:
                return None, "Year must be between 0 and 9999."
        except ValueError:
            return None, "Year must be a number."
    if page_count.strip():
        try:
            pages_val = int(page_count.strip())
            if pages_val < 1:
                return None, "Page count must be at least 1."
        except ValueError:
            return None, "Page count must be a number."

    return {
        "title": title,
        "author": author,
        "year": year_val,
        "notes": notes_val,
        "category": category_val,
        "isbn": isbn_val,
        "page_count": pages_val,
        "available": available_val,
    }, None


def _form_values(
    *,
    title: str,
    author: str,
    year: str,
    notes: str,
    category: str,
    isbn: str,
    page_count: str,
    available: str | None,
) -> dict:
    return {
        "title": title,
        "author": author,
        "year": year,
        "notes": notes,
        "category": category or "fiction",
        "isbn": isbn,
        "page_count": page_count,
        "available": available in {"1", "true", "on", "yes"},
    }


def _form_values_from_book(book: dict) -> dict:
    return {
        "title": book["title"],
        "author": book["author"],
        "year": "" if book["year"] is None else str(book["year"]),
        "notes": book["notes"] or "",
        "category": book["category"],
        "isbn": book["isbn"] or "",
        "page_count": "" if book["page_count"] is None else str(book["page_count"]),
        "available": bool(book["available"]),
    }


@router.get("/books", response_class=HTMLResponse)
async def books_page(
    request: Request,
    user: dict = Depends(require_user_html),
    page: int = Query(1, ge=1),
    size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=100),
    ordering: str | None = Query(None),
    q: str | None = Query(None),
):
    data = await _books_page_data(
        base_path="/ui/books",
        page=page,
        size=size,
        ordering=ordering,
        q=q,
    )
    template = (
        "partials/books_table.html"
        if _wants_books_partial(request)
        else "books.html"
    )
    return templates.TemplateResponse(request, template, _ctx(request, user, **data))


@router.get("/books/search", response_class=HTMLResponse)
async def books_search_page(
    request: Request,
    user: dict = Depends(require_user_html),
    page: int = Query(1, ge=1),
    size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=100),
    ordering: str | None = Query(None),
    q: str | None = Query(None),
    category: str | None = Query(None),
    available: str | None = Query(None),
    added_by_user_id: str | None = Query(None),
    year_min: str | None = Query(None),
    year_max: str | None = Query(None),
):
    try:
        ymin = _parse_optional_int(year_min)
        ymax = _parse_optional_int(year_max)
        added_by = _parse_optional_int(added_by_user_id)
    except ValueError:
        return HTMLResponse("Invalid filter value", status_code=400)

    users = await list_users()
    added_by_label = None
    if added_by is not None:
        added_by_label = next(
            (u["username"] for u in users if u["id"] == added_by),
            f"user #{added_by}",
        )

    data = await _books_page_data(
        base_path="/ui/books/search",
        page=page,
        size=size,
        ordering=ordering,
        q=q,
        category=category,
        available=available,
        added_by_user_id=added_by,
        added_by_label=added_by_label,
        year_min=ymin,
        year_max=ymax,
    )
    template = (
        "partials/books_table.html"
        if _wants_books_partial(request)
        else "books_search.html"
    )
    return templates.TemplateResponse(
        request,
        template,
        _ctx(request, user, filter_users=users, active="books-search", **data),
    )


@router.get("/books/new", response_class=HTMLResponse)
async def new_book_page(
    request: Request,
    user: dict = Depends(require_editor_html),
):
    return templates.TemplateResponse(
        request,
        "book_new.html",
        _ctx(
            request,
            user,
            form_error=None,
            values=_form_values(
                title="",
                author="",
                year="",
                notes="",
                category="fiction",
                isbn="",
                page_count="",
                available="1",
            ),
        ),
    )


@router.post(
    "/books",
    response_class=HTMLResponse,
    dependencies=[Depends(verify_csrf)],
)
async def create_book(
    request: Request,
    user: dict = Depends(require_editor_html),
    title: str = Form(...),
    author: str = Form(...),
    year: str = Form(""),
    notes: str = Form(""),
    category: str = Form("other"),
    isbn: str = Form(""),
    page_count: str = Form(""),
    available: str | None = Form(None),
    page: int = Form(1),
    size: int = Form(DEFAULT_PAGE_SIZE),
    ordering: str = Form(""),
    q: str = Form(""),
    next: str = Form(""),
):
    # Unchecked checkbox omits the field → treat as unavailable.
    payload, form_error = _parse_book_form(
        title=title,
        author=author,
        year=year,
        notes=notes,
        category=category,
        isbn=isbn,
        page_count=page_count,
        available=available if available is not None else "0",
    )
    created = None
    if form_error is None and payload is not None:
        created = await books_repo.create_book(
            payload["title"],
            payload["author"],
            year=payload["year"],
            notes=payload["notes"],
            category=payload["category"],
            isbn=payload["isbn"],
            page_count=payload["page_count"],
            available=payload["available"],
            added_by_user_id=user["id"],
        )
        page = 1

    if next == "detail":
        if created is not None:
            return RedirectResponse(url=f"/ui/books/{created['id']}", status_code=303)
        return templates.TemplateResponse(
            request,
            "book_new.html",
            _ctx(
                request,
                user,
                form_error=form_error,
                values=_form_values(
                    title=title,
                    author=author,
                    year=year,
                    notes=notes,
                    category=category,
                    isbn=isbn,
                    page_count=page_count,
                    available=available,
                ),
            ),
            status_code=400,
        )

    data = await _books_page_data(
        base_path="/ui/books",
        page=page,
        size=size,
        ordering=ordering or None,
        q=q or None,
    )
    return templates.TemplateResponse(
        request,
        "partials/books_table.html",
        _ctx(request, user, form_error=form_error, **data),
        status_code=400 if form_error else 200,
    )


@router.get("/books/{book_id}/edit", response_class=HTMLResponse)
async def edit_book_form(
    request: Request,
    book_id: str,
    user: dict = Depends(require_editor_html),
    place: dict[str, str] = Depends(_list_place),
):
    book = await books_repo.get_book(book_id)
    if book is None:
        if _wants_books_partial(request):
            return HTMLResponse("Book not found", status_code=404)
        return await render_not_found(request)
    if _wants_books_partial(request):
        return templates.TemplateResponse(
            request,
            "partials/book_edit_row.html",
            _ctx(
                request,
                user,
                book=book,
                page=1,
                size=DEFAULT_PAGE_SIZE,
                q="",
                list_base="/ui/books",
                results_query=urlencode(
                    {"page": 1, "size": DEFAULT_PAGE_SIZE, "return_to": "list"}
                ),
            ),
        )
    return templates.TemplateResponse(
        request,
        "book_edit.html",
        _ctx(
            request,
            user,
            book=book,
            form_error=None,
            values=_form_values_from_book(book),
            **_book_page_urls(book_id, place),
        ),
    )


@router.post(
    "/books/{book_id}/edit",
    response_class=HTMLResponse,
    dependencies=[Depends(verify_csrf)],
)
async def save_book_page(
    request: Request,
    book_id: str,
    user: dict = Depends(require_editor_html),
    place: dict[str, str] = Depends(_list_place),
    title: str = Form(...),
    author: str = Form(...),
    year: str = Form(""),
    notes: str = Form(""),
    category: str = Form("other"),
    isbn: str = Form(""),
    page_count: str = Form(""),
    available: str | None = Form(None),
):
    payload, form_error = _parse_book_form(
        title=title,
        author=author,
        year=year,
        notes=notes,
        category=category,
        isbn=isbn,
        page_count=page_count,
        available=available if available is not None else "0",
    )
    if form_error or payload is None:
        return templates.TemplateResponse(
            request,
            "book_edit.html",
            _ctx(
                request,
                user,
                book={"id": book_id, "title": title},
                form_error=form_error,
                values=_form_values(
                    title=title,
                    author=author,
                    year=year,
                    notes=notes,
                    category=category,
                    isbn=isbn,
                    page_count=page_count,
                    available=available,
                ),
                **_book_page_urls(book_id, place),
            ),
            status_code=400,
        )
    book = await books_repo.update_book(
        book_id,
        title=payload["title"],
        author=payload["author"],
        year=payload["year"],
        year_set=True,
        notes=payload["notes"],
        notes_set=True,
        category=payload["category"],
        isbn=payload["isbn"],
        isbn_set=True,
        page_count=payload["page_count"],
        page_count_set=True,
        available=payload["available"],
    )
    if book is None:
        return await render_not_found(request)
    _remember_toast(request, "Book saved")
    return RedirectResponse(
        url=_book_page_urls(book["id"], place)["detail_href"],
        status_code=303,
    )


@router.get("/books/{book_id}", response_class=HTMLResponse)
async def book_page(
    request: Request,
    book_id: str,
    user: dict = Depends(require_user_html),
    place: dict[str, str] = Depends(_list_place),
):
    book = await books_repo.get_book(book_id)
    if book is None:
        return await render_not_found(request)
    return templates.TemplateResponse(
        request,
        "book_detail.html",
        _ctx(request, user, book=book, **_book_page_urls(book_id, place)),
    )


@router.get("/books/{book_id}/row", response_class=HTMLResponse)
async def book_row(
    request: Request,
    book_id: str,
    user: dict = Depends(require_user_html),
):
    book = await books_repo.get_book(book_id)
    if book is None:
        return HTMLResponse("Book not found", status_code=404)
    return templates.TemplateResponse(
        request,
        "partials/book_row.html",
        _ctx(
            request,
            user,
            book=book,
            page=1,
            size=DEFAULT_PAGE_SIZE,
            q="",
            list_base="/ui/books",
            results_query=urlencode(
                {"page": 1, "size": DEFAULT_PAGE_SIZE, "return_to": "list"}
            ),
        ),
    )


@router.put(
    "/books/{book_id}",
    response_class=HTMLResponse,
    dependencies=[Depends(verify_csrf)],
)
async def update_book(
    request: Request,
    book_id: str,
    user: dict = Depends(require_editor_html),
    title: str = Form(...),
    author: str = Form(...),
    year: str = Form(""),
    notes: str = Form(""),
    category: str = Form("other"),
    isbn: str = Form(""),
    page_count: str = Form(""),
    available: str | None = Form(None),
):
    payload, form_error = _parse_book_form(
        title=title,
        author=author,
        year=year,
        notes=notes,
        category=category,
        isbn=isbn,
        page_count=page_count,
        available=available if available is not None else "0",
    )
    if form_error or payload is None:
        return HTMLResponse(form_error or "Invalid form", status_code=400)

    book = await books_repo.update_book(
        book_id,
        title=payload["title"],
        author=payload["author"],
        year=payload["year"],
        year_set=True,
        notes=payload["notes"],
        notes_set=True,
        category=payload["category"],
        isbn=payload["isbn"],
        isbn_set=True,
        page_count=payload["page_count"],
        page_count_set=True,
        available=payload["available"],
    )
    if book is None:
        return HTMLResponse("Book not found", status_code=404)
    response = templates.TemplateResponse(
        request,
        "partials/book_row.html",
        _ctx(
            request,
            user,
            book=book,
            page=1,
            size=DEFAULT_PAGE_SIZE,
            q="",
            list_base="/ui/books",
            results_query=urlencode(
                {"page": 1, "size": DEFAULT_PAGE_SIZE, "return_to": "list"}
            ),
        ),
    )
    response.headers["HX-Trigger"] = json.dumps(
        {"showToast": {"message": "Book saved", "level": "ok"}}
    )
    return response


@router.delete(
    "/books/{book_id}",
    response_class=HTMLResponse,
    dependencies=[Depends(verify_csrf)],
)
async def delete_book(
    request: Request,
    book_id: str,
    user: dict = Depends(require_editor_html),
    page: int = Query(1, ge=1),
    size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=100),
    ordering: str | None = Query(None),
    q: str | None = Query(None),
    category: str | None = Query(None),
    available: str | None = Query(None),
    added_by_user_id: str | None = Query(None),
    year_min: str | None = Query(None),
    year_max: str | None = Query(None),
    return_to: str = Query("list"),
    redirect: int = Query(0, ge=0, le=1),
):
    await books_repo.delete_book(book_id)
    try:
        ymin = _parse_optional_int(year_min)
        ymax = _parse_optional_int(year_max)
        added_by = _parse_optional_int(added_by_user_id)
    except ValueError:
        return HTMLResponse("Invalid filter value", status_code=400)

    if redirect:
        _remember_toast(request, "Book deleted")
        if _has_list_query(request):
            list_href, _, _ = _list_return(
                page=page,
                size=size,
                ordering=ordering,
                q=q,
                category=category,
                available=available,
                added_by_user_id=added_by,
                year_min=ymin,
                year_max=ymax,
                return_to=return_to,
            )
        else:
            list_href = "/ui/books"
        response = HTMLResponse("")
        response.headers["HX-Redirect"] = list_href
        return response

    base_path = "/ui/books/search" if return_to == "search" else "/ui/books"
    added_by_label = None
    if added_by is not None:
        users = await list_users()
        added_by_label = next(
            (u["username"] for u in users if u["id"] == added_by),
            f"user #{added_by}",
        )

    async def _reload(page_num: int) -> dict:
        return await _books_page_data(
            base_path=base_path,
            page=page_num,
            size=size,
            ordering=ordering,
            q=q,
            category=category,
            available=available,
            added_by_user_id=added_by,
            added_by_label=added_by_label,
            year_min=ymin,
            year_max=ymax,
        )

    data = await _reload(page)
    if data["total"] and page > data["total_pages"]:
        data = await _reload(data["total_pages"])
    response = templates.TemplateResponse(
        request,
        "partials/books_table.html",
        _ctx(request, user, **data),
    )
    response.headers["HX-Trigger"] = json.dumps(
        {"showToast": {"message": "Book deleted", "level": "ok"}}
    )
    return response


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(
    request: Request,
    user: dict = Depends(require_admin_html),
):
    users = await list_users()
    return templates.TemplateResponse(
        request,
        "admin_users.html",
        _ctx(
            request,
            user,
            users=users,
            roles=sorted(ROLES),
            form_error=None,
            form_ok=None,
            active="staff",
        ),
    )


@router.post(
    "/admin/users/{user_id}/role",
    response_class=HTMLResponse,
    dependencies=[Depends(verify_csrf)],
)
async def admin_set_role(
    request: Request,
    user_id: int,
    user: dict = Depends(require_admin_html),
    role: str = Form(...),
):
    role = normalize_role(role.strip())
    form_error = None
    form_ok = None

    if role not in ROLES:
        form_error = "Invalid role."
    else:
        target = next((u for u in await list_users() if u["id"] == user_id), None)
        if target is None:
            form_error = "User not found."
        elif (
            target["role"] == "admin"
            and role != "admin"
            and await count_admins() <= 1
        ):
            form_error = "Cannot demote the last admin."
        else:
            updated = await set_user_role(user_id, role)
            if updated is None:
                form_error = "User not found."
            else:
                form_ok = f"Updated {updated['username']} to {updated['role']}."

    users = await list_users()
    return templates.TemplateResponse(
        request,
        "partials/admin_users_table.html",
        _ctx(
            request,
            user,
            users=users,
            roles=sorted(ROLES),
            form_error=form_error,
            form_ok=form_ok,
            active="staff",
        ),
        status_code=400 if form_error else 200,
    )
