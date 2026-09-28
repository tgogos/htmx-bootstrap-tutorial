"""SQL helpers for the books table.

List/get use a LEFT JOIN to users so added_by_username is loaded in one query
(avoid N+1: do not call get_user_by_id per book row).
"""

from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from typing import Any, Optional
from uuid import uuid4

from app.db.connection import get_connection

BOOK_CATEGORIES = frozenset(
    {
        "fiction",
        "nonfiction",
        "scifi",
        "fantasy",
        "mystery",
        "biography",
        "other",
    }
)

DEFAULT_ORDERING = "title"

# Allowlisted only. Never interpolate a raw query value into ORDER BY.
ORDER_SQL: dict[str, str] = {
    "title": "b.title COLLATE NOCASE ASC",
    "-title": "b.title COLLATE NOCASE DESC",
    "author": "b.author COLLATE NOCASE ASC",
    "-author": "b.author COLLATE NOCASE DESC",
    "category": "b.category COLLATE NOCASE ASC",
    "-category": "b.category COLLATE NOCASE DESC",
    "year": "b.year IS NULL ASC, b.year ASC",
    "-year": "b.year IS NULL ASC, b.year DESC",
    "page_count": "b.page_count IS NULL ASC, b.page_count ASC",
    "-page_count": "b.page_count IS NULL ASC, b.page_count DESC",
    "available": "b.available ASC",
    "-available": "b.available DESC",
    "added_by": "u.username COLLATE NOCASE ASC",
    "-added_by": "u.username COLLATE NOCASE DESC",
}


def normalize_ordering(ordering: Optional[str]) -> str:
    if ordering and ordering in ORDER_SQL:
        return ordering
    return DEFAULT_ORDERING


_BOOK_SELECT = """
    SELECT
        b.id,
        b.title,
        b.author,
        b.year,
        b.notes,
        b.category,
        b.isbn,
        b.page_count,
        b.available,
        b.added_by_user_id,
        u.username AS added_by_username,
        b.created_at,
        b.updated_at
    FROM books b
    LEFT JOIN users u ON u.id = b.added_by_user_id
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_category(category: Optional[str]) -> str:
    if category and category in BOOK_CATEGORIES:
        return category
    return "other"


def _row_to_dict(row) -> dict[str, Any]:
    keys = row.keys()
    available = row["available"]
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "notes": row["notes"],
        "category": normalize_category(row["category"] if "category" in keys else None),
        "isbn": row["isbn"] if "isbn" in keys else None,
        "page_count": row["page_count"] if "page_count" in keys else None,
        "available": bool(available) if available is not None else True,
        "added_by_user_id": (
            row["added_by_user_id"] if "added_by_user_id" in keys else None
        ),
        "added_by_username": (
            row["added_by_username"] if "added_by_username" in keys else None
        ),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _build_filters(
    *,
    q: Optional[str] = None,
    category: Optional[str] = None,
    available: Optional[bool] = None,
    added_by_user_id: Optional[int] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    q = (q or "").strip() or None
    if q:
        like = f"%{q}%"
        clauses.append(
            "("
            "b.title LIKE ? COLLATE NOCASE OR "
            "b.author LIKE ? COLLATE NOCASE OR "
            "IFNULL(b.isbn, '') LIKE ? COLLATE NOCASE"
            ")"
        )
        params.extend([like, like, like])

    if category and category in BOOK_CATEGORIES:
        clauses.append("b.category = ?")
        params.append(category)

    if available is not None:
        clauses.append("b.available = ?")
        params.append(1 if available else 0)

    if added_by_user_id is not None:
        clauses.append("b.added_by_user_id = ?")
        params.append(added_by_user_id)

    if year_min is not None:
        clauses.append("b.year IS NOT NULL AND b.year >= ?")
        params.append(year_min)

    if year_max is not None:
        clauses.append("b.year IS NOT NULL AND b.year <= ?")
        params.append(year_max)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


async def create_book(
    title: str,
    author: str,
    *,
    year: Optional[int] = None,
    notes: Optional[str] = None,
    category: str = "other",
    isbn: Optional[str] = None,
    page_count: Optional[int] = None,
    available: bool = True,
    added_by_user_id: Optional[int] = None,
) -> dict[str, Any]:
    conn = get_connection()
    book_id = str(uuid4())
    now = _utcnow()
    await conn.execute(
        """
        INSERT INTO books (
            id, title, author, year, notes, category, isbn, page_count,
            available, added_by_user_id, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            book_id,
            title,
            author,
            year,
            notes,
            normalize_category(category),
            isbn,
            page_count,
            1 if available else 0,
            added_by_user_id,
            now,
            now,
        ),
    )
    await conn.commit()
    return await get_book(book_id)  # type: ignore[return-value]


async def get_book(book_id: str) -> Optional[dict[str, Any]]:
    conn = get_connection()
    async with conn.execute(
        _BOOK_SELECT + " WHERE b.id = ?",
        (book_id,),
    ) as cursor:
        row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def list_books(
    page: int = 1,
    size: int = 10,
    *,
    q: Optional[str] = None,
    category: Optional[str] = None,
    available: Optional[bool] = None,
    added_by_user_id: Optional[int] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    ordering: Optional[str] = None,
) -> tuple[list[dict[str, Any]], int]:
    """List books with filters. Username comes from JOIN (not per-row lookups)."""
    conn = get_connection()
    order_sql = ORDER_SQL[normalize_ordering(ordering)]
    where, params = _build_filters(
        q=q,
        category=category,
        available=available,
        added_by_user_id=added_by_user_id,
        year_min=year_min,
        year_max=year_max,
    )

    async with conn.execute(
        f"SELECT COUNT(*) AS c FROM books b {where}",
        params,
    ) as cursor:
        total = int((await cursor.fetchone())["c"])

    offset = (page - 1) * size
    async with conn.execute(
        f"""
        {_BOOK_SELECT}
        {where}
        ORDER BY {order_sql}, b.id ASC
        LIMIT ? OFFSET ?
        """,
        [*params, size, offset],
    ) as cursor:
        rows = await cursor.fetchall()

    return [_row_to_dict(r) for r in rows], total


def total_pages(total: int, size: int) -> int:
    return ceil(total / size) if total else 0


async def update_book(
    book_id: str,
    *,
    title: Optional[str] = None,
    author: Optional[str] = None,
    year: Optional[int] = None,
    year_set: bool = False,
    notes: Optional[str] = None,
    notes_set: bool = False,
    category: Optional[str] = None,
    isbn: Optional[str] = None,
    isbn_set: bool = False,
    page_count: Optional[int] = None,
    page_count_set: bool = False,
    available: Optional[bool] = None,
) -> Optional[dict[str, Any]]:
    existing = await get_book(book_id)
    if existing is None:
        return None

    new_title = title if title is not None else existing["title"]
    new_author = author if author is not None else existing["author"]
    if year_set:
        new_year = year
    else:
        new_year = existing["year"] if year is None else year
    if notes_set:
        new_notes = notes
    else:
        new_notes = existing["notes"] if notes is None else notes
    new_category = (
        normalize_category(category) if category is not None else existing["category"]
    )
    if isbn_set:
        new_isbn = isbn
    else:
        new_isbn = existing["isbn"] if isbn is None else isbn
    if page_count_set:
        new_pages = page_count
    else:
        new_pages = existing["page_count"] if page_count is None else page_count
    if available is None:
        new_available = existing["available"]
    else:
        new_available = available

    now = _utcnow()
    conn = get_connection()
    await conn.execute(
        """
        UPDATE books
        SET title = ?, author = ?, year = ?, notes = ?, category = ?,
            isbn = ?, page_count = ?, available = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            new_title,
            new_author,
            new_year,
            new_notes,
            new_category,
            new_isbn,
            new_pages,
            1 if new_available else 0,
            now,
            book_id,
        ),
    )
    await conn.commit()
    return await get_book(book_id)


async def delete_book(book_id: str) -> bool:
    conn = get_connection()
    cursor = await conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    await conn.commit()
    return cursor.rowcount > 0


async def clear_books() -> None:
    """Delete all books (test helper)."""
    conn = get_connection()
    await conn.execute("DELETE FROM books")
    await conn.commit()
