"""User queries against SQLite."""

from __future__ import annotations

from typing import Any, Optional

from app.db.connection import get_connection

ROLES = frozenset({"viewer", "editor", "admin"})
ROLE_RANK = {"viewer": 1, "editor": 2, "admin": 3}


def normalize_role(role: Optional[str]) -> str:
    if role in ROLES:
        return role  # type: ignore[return-value]
    return "viewer"


def role_at_least(role: str, minimum: str) -> bool:
    return ROLE_RANK.get(normalize_role(role), 0) >= ROLE_RANK[minimum]


def _row_to_user(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "username": row["username"],
        "password_hash": row["password_hash"],
        "role": normalize_role(row["role"] if "role" in row.keys() else None),
        "created_at": row["created_at"],
    }


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "username": user["username"],
        "role": normalize_role(user.get("role")),
    }


async def get_user_by_id(user_id: int) -> Optional[dict[str, Any]]:
    conn = get_connection()
    async with conn.execute(
        "SELECT id, username, password_hash, role, created_at FROM users WHERE id = ?",
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return None
    return _row_to_user(row)


async def get_user_by_username(username: str) -> Optional[dict[str, Any]]:
    conn = get_connection()
    async with conn.execute(
        "SELECT id, username, password_hash, role, created_at FROM users WHERE username = ?",
        (username,),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return None
    return _row_to_user(row)


async def count_users() -> int:
    conn = get_connection()
    async with conn.execute("SELECT COUNT(*) AS c FROM users") as cursor:
        row = await cursor.fetchone()
    return int(row["c"])


async def count_admins() -> int:
    conn = get_connection()
    async with conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE role = 'admin'"
    ) as cursor:
        row = await cursor.fetchone()
    return int(row["c"])


async def list_users() -> list[dict[str, Any]]:
    conn = get_connection()
    async with conn.execute(
        """
        SELECT id, username, password_hash, role, created_at
        FROM users
        ORDER BY username COLLATE NOCASE
        """
    ) as cursor:
        rows = await cursor.fetchall()
    return [_row_to_user(r) for r in rows]


async def create_user(
    username: str,
    password_hash: str,
    role: str = "viewer",
) -> dict[str, Any]:
    role = normalize_role(role)
    conn = get_connection()
    cursor = await conn.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, password_hash, role),
    )
    await conn.commit()
    user = await get_user_by_id(cursor.lastrowid)
    assert user is not None
    return user


async def set_user_role(user_id: int, role: str) -> Optional[dict[str, Any]]:
    role = normalize_role(role)
    if role not in ROLES:
        raise ValueError(f"Invalid role: {role}")
    conn = get_connection()
    cursor = await conn.execute(
        "UPDATE users SET role = ? WHERE id = ?",
        (role, user_id),
    )
    await conn.commit()
    if cursor.rowcount == 0:
        return None
    return await get_user_by_id(user_id)
