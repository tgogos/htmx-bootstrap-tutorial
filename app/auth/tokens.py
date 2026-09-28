"""Opaque API token helpers (SQLite)."""

from __future__ import annotations

import hashlib
import secrets
from typing import Any, Optional

from app.db.connection import get_connection


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


async def create_token(user_id: int) -> str:
    """Create a token for user_id; return the plaintext token (shown once)."""
    raw = secrets.token_urlsafe(32)
    conn = get_connection()
    await conn.execute(
        "INSERT INTO api_tokens (user_id, token_hash) VALUES (?, ?)",
        (user_id, hash_token(raw)),
    )
    await conn.commit()
    return raw


async def get_user_by_token(raw_token: str) -> Optional[dict[str, Any]]:
    """Resolve a plaintext Bearer token to a public user dict, or None."""
    if not raw_token:
        return None
    from app.auth.users import normalize_role

    conn = get_connection()
    async with conn.execute(
        """
        SELECT u.id, u.username, u.role
        FROM api_tokens t
        JOIN users u ON u.id = t.user_id
        WHERE t.token_hash = ?
        """,
        (hash_token(raw_token),),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "role": normalize_role(row["role"]),
    }


async def revoke_token(raw_token: str) -> bool:
    """Delete a token by plaintext value. Returns True if a row was removed."""
    conn = get_connection()
    cursor = await conn.execute(
        "DELETE FROM api_tokens WHERE token_hash = ?",
        (hash_token(raw_token),),
    )
    await conn.commit()
    return cursor.rowcount > 0
