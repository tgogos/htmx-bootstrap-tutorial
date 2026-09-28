"""SQLite database utilities (removable for NoSQL-only forks)."""

from app.db.connection import (
    check_sqlite_connection,
    close_sqlite,
    connect_to_sqlite,
    get_connection,
)

__all__ = [
    "check_sqlite_connection",
    "close_sqlite",
    "connect_to_sqlite",
    "get_connection",
]
