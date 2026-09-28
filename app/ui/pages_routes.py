"""Bootstrap admin pages (dashboard shell and specimen pages)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth.deps import get_or_create_csrf_token, get_session_user, require_user_html
from app.auth.users import role_at_least
from app.ui.paths import TEMPLATES_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# path, template, active, nav_group, extra_css, extra_js, main_class
SHELL_PAGES: list[tuple] = [
    (
        "/dashboard",
        "pages/dashboard.html",
        "dashboard",
        None,
        [],
        [
            "/static/vendor/chart.js/chart.umd.min.js",
            "/static/js/dashboard.js",
        ],
        "",
    ),
    ("/users", "pages/users.html", "users", None, [], [], ""),
    ("/forms", "pages/forms.html", "forms", None, [], [], ""),
    ("/tables", "pages/tables.html", "tables", None, [], [], ""),
    (
        "/palette-lab",
        "pages/palette_lab.html",
        "palette-lab",
        None,
        ["/static/css/palette-lab.css"],
        ["/static/js/palette-lab.js"],
        "",
    ),
    (
        "/components",
        "pages/components.html",
        "components",
        "components",
        [],
        [],
        "",
    ),
    (
        "/cheatsheet",
        "pages/cheatsheet.html",
        "cheatsheet",
        "cheatsheet",
        ["/static/css/cheatsheet.css"],
        ["/static/js/cheatsheet.js"],
        "bd-cheatsheet",
    ),
    ("/settings", "pages/settings.html", "settings", None, [], [], ""),
    ("/blank", "pages/blank.html", "blank", None, [], [], ""),
    ("/404", "pages/not_found.html", "", None, [], [], ""),
]

HEADER_PAGES = (
    "simple",
    "centered",
    "buttons",
    "dark",
    "account",
    "product",
    "double",
    "icons",
)
SIDEBAR_PAGES = ("dark", "light", "icons", "collapsible", "list-group")


def shell_ctx(
    request: Request,
    user: dict | None,
    *,
    active: str,
    nav_group: str | None = None,
    extra_css: list[str] | None = None,
    extra_js: list[str] | None = None,
    main_class: str = "",
) -> dict:
    return {
        "request": request,
        "user": user,
        "csrf_token": get_or_create_csrf_token(request),
        "is_admin": bool(user) and role_at_least(user["role"], "admin"),
        "active": active,
        "nav_group": nav_group,
        "extra_css": extra_css or [],
        "extra_js": extra_js or [],
        "main_class": main_class,
    }


def _page(
    path: str,
    template_name: str,
    active: str,
    nav_group: str | None,
    extra_css: list[str],
    extra_js: list[str],
    main_class: str,
):
    async def handler(
        request: Request,
        user: dict = Depends(require_user_html),
    ):
        return templates.TemplateResponse(
            request,
            template_name,
            shell_ctx(
                request,
                user,
                active=active,
                nav_group=nav_group,
                extra_css=extra_css,
                extra_js=extra_js,
                main_class=main_class,
            ),
        )

    handler.__name__ = "page_" + path.strip("/").replace("/", "_").replace("-", "_")
    return path, handler


for _spec in SHELL_PAGES:
    _path, _handler = _page(*_spec)
    router.add_api_route(
        _path, _handler, methods=["GET"], response_class=HTMLResponse, include_in_schema=False
    )

for _name in HEADER_PAGES:
    _path, _handler = _page(
        f"/headers/{_name}",
        f"gallery/headers_{_name}.html",
        f"headers-{_name}",
        "headers",
        ["/static/css/headers.css"],
        [],
        "",
    )
    router.add_api_route(
        _path, _handler, methods=["GET"], response_class=HTMLResponse, include_in_schema=False
    )

for _name in SIDEBAR_PAGES:
    _template = "gallery/sidebars_" + _name.replace("-", "_") + ".html"
    _path, _handler = _page(
        f"/sidebars/{_name}",
        _template,
        f"sidebars-{_name}",
        "sidebars",
        ["/static/css/sidebars.css"],
        [],
        "",
    )
    router.add_api_route(
        _path, _handler, methods=["GET"], response_class=HTMLResponse, include_in_schema=False
    )


async def render_not_found(request: Request) -> HTMLResponse:
    user = await get_session_user(request)
    return templates.TemplateResponse(
        request,
        "pages/not_found.html",
        shell_ctx(request, user, active=""),
        status_code=404,
    )
