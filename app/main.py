# Standard library imports
import logging
from contextlib import asynccontextmanager

# Third-party imports
from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

# Local imports
from app.auth.exceptions import LoginRequired
from app.core import config
from app.core.logging import setup_logging
from app.routes import root, items, db_items, books, api_auth
from app.web import auth_routes, books_routes, pages_routes
from app.web.paths import STATIC_DIR

logger = logging.getLogger(__name__)

description = """
### Root
- `/` redirects to the admin dashboard (`/ui/dashboard`).
- Health-check endpoint.

### Items (demo)
- CRUD operations for items (in-memory storage).

### Database Items (demo)
- CRUD operations for items (MongoDB storage).

### API auth
- `POST /api/auth/token` — username/password → opaque Bearer token.
- `DELETE /api/auth/token` — revoke the current Bearer token.
- `GET /api/auth/me` — current user (Bearer or session), includes role.

### Books (primary)
- CRUD under `/api/books` (SQLite).
- Reads require login (viewer+); writes require editor or admin.
- Dual auth: Bearer token, or session cookie + CSRF on mutations.

### Web UI
- Bootstrap admin shell + HTMX under `/ui`; browser login under `/auth` (not listed in this schema).
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.utils.mongo import connect_to_mongo, close_mongo_connection
    from app.db.connection import connect_to_sqlite, close_sqlite
    from app.auth.seed import seed_demo_user

    setup_logging()
    logger.info(
        "Starting %s (%s, LOG_LEVEL=%s)",
        app.title,
        config.ENVIRONMENT,
        config.LOG_LEVEL,
    )
    if config.DEBUG:
        config.log_config_values()
    await connect_to_mongo()
    await connect_to_sqlite()
    await seed_demo_user()
    yield
    logger.info("Shutting down")
    await close_sqlite()
    await close_mongo_connection()


app = FastAPI(
    title="FastAPI HTMX Bootstrap",
    description=description,
    summary="FastAPI + HTMX admin with a Bootstrap shell",
    version=config.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=config.SECRET_KEY,
    session_cookie=config.SESSION_COOKIE_NAME,
    same_site="lax",
    https_only=False,
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _wants_html(request: Request) -> bool:
    path = request.url.path
    if path.startswith(
        ("/api", "/items", "/db-items", "/static", "/docs", "/redoc", "/openapi")
    ):
        return False
    return "text/html" in request.headers.get("accept", "")


@app.exception_handler(LoginRequired)
async def login_required_handler(request: Request, exc: LoginRequired):
    return RedirectResponse(url="/auth/login", status_code=303)


@app.exception_handler(StarletteHTTPException)
async def html_not_found_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and _wants_html(request):
        return await pages_routes.render_not_found(request)
    return await http_exception_handler(request, exc)


# JSON API (demos stay at top level; primary path under /api)
app.include_router(root.router, prefix="", tags=["root"])
app.include_router(items.router, prefix="/items", tags=["items"])
app.include_router(db_items.router, prefix="/db-items", tags=["database-items"])
app.include_router(api_auth.router, prefix="/api/auth", tags=["auth-api"])
app.include_router(books.router, prefix="/api/books", tags=["books"])

# HTML / HTMX (removable with app/web/; omitted from OpenAPI — browser session, not Bearer)
app.include_router(
    auth_routes.router, prefix="/auth", tags=["auth-web"], include_in_schema=False
)
app.include_router(
    pages_routes.router, prefix="/ui", tags=["ui"], include_in_schema=False
)
app.include_router(
    books_routes.router, prefix="/ui", tags=["ui"], include_in_schema=False
)
