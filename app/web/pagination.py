"""Shared page-size choices for HTML list panels."""

from __future__ import annotations

PAGE_SIZES = (10, 25, 50, 100)
DEFAULT_PAGE_SIZE = 10


def page_size(size: int) -> int:
    if size in PAGE_SIZES:
        return size
    return DEFAULT_PAGE_SIZE


def sort_column_state(ordering: str, column: str) -> str | None:
    """Return asc, desc, or None for a table header."""
    if ordering == column:
        return "asc"
    if ordering == f"-{column}":
        return "desc"
    return None
