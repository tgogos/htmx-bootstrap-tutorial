"""HTML / HTMX routes for books UI and admin users."""

from __future__ import annotations

import json
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse
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
from app.web.pagination import DEFAULT_PAGE_SIZE, PAGE_SIZES, page_size, sort_column_state
from app.web.paths import TEMPLATES_DIR

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
    return ctx


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
    return f"{base}?{urlencode(params)}"


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
        "page": page,
        "size": size,
        "ordering": ordering,
        "return_to": return_to,
    }
    if q:
        results_params["q"] = q
    if cat:
        results_params["category"] = cat
    if available and available != "any":
        results_params["available"] = available
    if added_by_user_id is not None:
        results_params["added_by_user_id"] = added_by_user_id
    if year_min is not None:
        results_params["year_min"] = year_min
    if year_max is not None:
        results_params["year_max"] = year_max

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
        if request.headers.get("HX-Request") == "true"
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
        if request.headers.get("HX-Request") == "true"
        else "books_search.html"
    )
    return templates.TemplateResponse(
        request,
        template,
        _ctx(request, user, filter_users=users, active="books-search", **data),
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
    if form_error is None and payload is not None:
        await books_repo.create_book(
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
):
    book = await books_repo.get_book(book_id)
    if book is None:
        return HTMLResponse("Book not found", status_code=404)
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
):
    await books_repo.delete_book(book_id)
    try:
        ymin = _parse_optional_int(year_min)
        ymax = _parse_optional_int(year_max)
        added_by = _parse_optional_int(added_by_user_id)
    except ValueError:
        return HTMLResponse("Invalid filter value", status_code=400)

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
