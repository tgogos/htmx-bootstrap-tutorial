"""FastAPI dependencies for session auth, Bearer tokens, roles, and CSRF."""

from __future__ import annotations

import secrets
from typing import Annotated, Any, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.exceptions import LoginRequired
from app.auth.tokens import get_user_by_token
from app.auth.users import get_user_by_id, public_user, role_at_least

SESSION_USER_KEY = "user_id"
SESSION_CSRF_KEY = "csrf_token"

_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Opaque token from POST /api/auth/token",
)


def get_or_create_csrf_token(request: Request) -> str:
    token = request.session.get(SESSION_CSRF_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[SESSION_CSRF_KEY] = token
    return token


async def verify_csrf(request: Request) -> None:
    """Validate CSRF from X-CSRF-Token header or csrf_token form field."""
    expected = request.session.get(SESSION_CSRF_KEY)
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing from session",
        )

    provided = request.headers.get("X-CSRF-Token")
    if not provided and request.method in _MUTATING_METHODS:
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            form = await request.form()
            provided = form.get("csrf_token")

    if provided != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )


ensure_csrf = verify_csrf


async def get_session_user(request: Request) -> Optional[dict[str, Any]]:
    """Resolve the logged-in user from the signed session cookie only."""
    user_id = request.session.get(SESSION_USER_KEY)
    if user_id is None:
        return None
    user = await get_user_by_id(int(user_id))
    if user is None:
        request.session.pop(SESSION_USER_KEY, None)
        return None
    return public_user(user)


get_current_user = get_session_user


async def get_api_user(
    request: Request,
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
) -> Optional[dict[str, Any]]:
    """Resolve user from Bearer token (preferred) or session cookie."""
    if credentials is not None and credentials.credentials:
        user = await get_user_by_token(credentials.credentials)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or unknown token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    return await get_session_user(request)


async def require_user(
    request: Request,
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ],
) -> dict[str, Any]:
    """Require auth for JSON API routes (Bearer or session)."""
    used_bearer = bool(credentials and credentials.credentials)

    if used_bearer:
        user = await get_user_by_token(credentials.credentials)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or unknown token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    else:
        user = await get_session_user(request)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not used_bearer and request.method in _MUTATING_METHODS:
        await verify_csrf(request)

    return user


async def require_editor(
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    if not role_at_least(user["role"], "editor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editor or admin role required",
        )
    return user


async def require_admin(
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    if not role_at_least(user["role"], "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user


async def require_user_html(request: Request) -> dict[str, Any]:
    """Require login for HTML routes; redirects via LoginRequired handler."""
    user = await get_session_user(request)
    if user is None:
        raise LoginRequired()
    return user


async def require_editor_html(request: Request) -> dict[str, Any]:
    user = await require_user_html(request)
    if not role_at_least(user["role"], "editor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editor or admin role required",
        )
    return user


async def require_admin_html(request: Request) -> dict[str, Any]:
    user = await require_user_html(request)
    if not role_at_least(user["role"], "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user
