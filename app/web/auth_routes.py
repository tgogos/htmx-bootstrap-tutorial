"""HTML auth routes: login / logout."""

import logging
import secrets

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth.deps import (
    SESSION_CSRF_KEY,
    SESSION_USER_KEY,
    get_current_user,
    get_or_create_csrf_token,
    verify_csrf,
)
from app.auth.passwords import verify_password
from app.auth.users import get_user_by_username
from app.web.paths import TEMPLATES_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
logger = logging.getLogger(__name__)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/ui/dashboard", status_code=303)
    csrf_token = get_or_create_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "user": None,
            "csrf_token": csrf_token,
            "error": None,
        },
    )


@router.post(
    "/login",
    response_class=HTMLResponse,
    dependencies=[Depends(verify_csrf)],
)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    db_user = await get_user_by_username(username.strip())
    if db_user is None or not verify_password(password, db_user["password_hash"]):
        logger.warning("Login failed for username=%s", username.strip())
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "user": None,
                "csrf_token": get_or_create_csrf_token(request),
                "error": "Invalid username or password.",
            },
            status_code=400,
        )

    request.session[SESSION_USER_KEY] = db_user["id"]
    # Rotate CSRF after authentication
    request.session[SESSION_CSRF_KEY] = secrets.token_urlsafe(32)
    return RedirectResponse(url="/ui/dashboard", status_code=303)


@router.post("/logout", dependencies=[Depends(verify_csrf)])
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=303)
