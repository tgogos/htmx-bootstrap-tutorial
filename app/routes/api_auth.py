"""JSON auth API: token issue, current user, and revoke."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.deps import require_user
from app.auth.passwords import verify_password
from app.auth.tokens import create_token, revoke_token
from app.auth.users import get_user_by_username
from app.models.auth import TokenRequest, TokenResponse, UserPublic

router = APIRouter()
logger = logging.getLogger(__name__)

# Require a Bearer token for revoke (session alone has no token to delete)
_bearer_required = HTTPBearer(
    auto_error=True,
    description="Opaque token from POST /api/auth/token",
)


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Issue an API Bearer token",
)
async def issue_token(body: TokenRequest) -> TokenResponse:
    user = await get_user_by_username(body.username.strip())
    if user is None or not verify_password(body.password, user["password_hash"]):
        logger.warning("API token issue failed for username=%s", body.username.strip())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    raw = await create_token(user["id"])
    return TokenResponse(access_token=raw)


@router.delete(
    "/token",
    status_code=204,
    summary="Revoke the current Bearer token",
)
async def revoke_current_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_required)],
) -> None:
    deleted = await revoke_token(credentials.credentials)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or unknown token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get(
    "/me",
    response_model=UserPublic,
    summary="Current user (session or Bearer)",
)
async def me(user: dict = Depends(require_user)) -> UserPublic:
    return UserPublic(
        id=user["id"],
        username=user["username"],
        role=user.get("role", "viewer"),
    )
