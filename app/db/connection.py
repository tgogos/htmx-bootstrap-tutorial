"""Async SQLite connection management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import aiosqlite

from app.core import config

logger = logging.getLogger(__name__)

_connection: Optional[aiosqlite.Connection] = None

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


async def connect_to_sqlite() -> aiosqlite.Connection:
    """Open SQLite, apply schema, and keep a process-wide connection."""
    global _connection

    db_path = config.sqlite_path_from_url()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    _connection = await aiosqlite.connect(db_path)
    _connection.row_factory = aiosqlite.Row
    await _connection.execute("PRAGMA foreign_keys = ON")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    await _connection.executescript(schema_sql)
    await _connection.commit()
    await _migrate_books_columns(_connection)

    logger.info("Connected to SQLite at %s", db_path)
    return _connection


async def _migrate_books_columns(conn: aiosqlite.Connection) -> None:
    """Add books columns introduced after the first schema (CREATE IF NOT EXISTS is a no-op)."""
    async with conn.execute("PRAGMA table_info(books)") as cursor:
        cols = {row["name"] for row in await cursor.fetchall()}
    if not cols:
        return

    alters: list[str] = []
    if "category" not in cols:
        alters.append(
            "ALTER TABLE books ADD COLUMN category TEXT NOT NULL DEFAULT 'other'"
        )
    if "isbn" not in cols:
        alters.append("ALTER TABLE books ADD COLUMN isbn TEXT")
    if "page_count" not in cols:
        alters.append("ALTER TABLE books ADD COLUMN page_count INTEGER")
    if "available" not in cols:
        alters.append(
            "ALTER TABLE books ADD COLUMN available INTEGER NOT NULL DEFAULT 1"
        )
    if "added_by_user_id" not in cols:
        alters.append("ALTER TABLE books ADD COLUMN added_by_user_id INTEGER")

    for sql in alters:
        await conn.execute(sql)
    if alters:
        await conn.commit()
        logger.info("Migrated books table (+%s columns)", len(alters))

    # Safe after columns exist (new DB via schema.sql, or ALTER above).
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_books_category ON books(category)"
    )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_books_available ON books(available)"
    )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_books_added_by ON books(added_by_user_id)"
    )
    await conn.commit()


async def close_sqlite() -> None:
    """Close the SQLite connection."""
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None
        logger.info("SQLite connection closed")


def get_connection() -> aiosqlite.Connection:
    """Return the active SQLite connection."""
    if _connection is None:
        raise RuntimeError("SQLite not connected. Call connect_to_sqlite() first.")
    return _connection


async def check_sqlite_connection() -> bool:
    """Return True if SQLite responds to a simple query."""
    try:
        if _connection is None:
            return False
        async with _connection.execute("SELECT 1") as cursor:
            row = await cursor.fetchone()
        return row is not None
    except Exception:
        return False
