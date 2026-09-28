"""Authentication helpers (session + opaque Bearer tokens + roles)."""

from app.auth.passwords import hash_password, verify_password
from app.auth.deps import (
    get_current_user,
    get_session_user,
    get_api_user,
    require_user,
    require_editor,
    require_admin,
    require_user_html,
    require_editor_html,
    require_admin_html,
    verify_csrf,
    ensure_csrf,
    get_or_create_csrf_token,
)

__all__ = [
    "hash_password",
    "verify_password",
    "get_current_user",
    "get_session_user",
    "get_api_user",
    "require_user",
    "require_editor",
    "require_admin",
    "require_user_html",
    "require_editor_html",
    "require_admin_html",
    "verify_csrf",
    "ensure_csrf",
    "get_or_create_csrf_token",
]
