# Engineering notes

Decisions for this boilerplate. Prefer simple, robust, boring.

This file is the source of truth for architecture and conventions. When a decision or the code changes, update this document in the same change so it stays accurate for future readers (and agents). Do not refer to chat threads, option letters, or temporary debate labels.

## Goals

- Mature shape (clear modules, auth, tests, Docker) without shortcuts that fight growth.
- One primary full-stack path; optional demos stay thin and removable.
- Async-first; raw SQL (no ORM); Pydantic at the HTTP edge only.
- **HTML-first / HTMX** for the browser UI; `/api` JSON for machines. Not an SPA.

## UI architecture (HTML-first)

Prefer boring, server-driven UI over client frameworks. Concrete HTMX usage is under **HTMX patterns in use**.

### Principles

| Principle | Meaning |
|-----------|---------|
| **Server owns the truth** | Pages and HTMX fragments are the UI. Do not grow a client-side app store or SPA router. |
| **HTML first** | First paint and list/filter/mutation flows are server-rendered HTML (Jinja + the Bootstrap admin shell). |
| **HTMX for interaction** | Search, filters, pagination, and forms use HTMX swaps. |
| **Small JS islands** | Vanilla JS only where the browser must own a bit of widget state (confirm modal, toasts, CSRF header, page-size select). Prefer one focused script (`app/web/static/js/app.js`). |
| **Progressive enhancement** | Pagination links keep usable `href`s; forms still work without JS where practical. |
| **Shareable URLs** | List/search use `hx-push-url`. |

### What not to add by default

- **No Alpine, React, Vue, Svelte, or similar** — local reactivity is not a reason. Add a client library only when a concrete widget cannot be done with HTMX + a small vanilla island, and document why in this file in the same change.
- **No SPA routing or frontend build step** — no Vite/Webpack app shell; static CSS/JS under `app/web/static/` is enough.
- **No client i18n framework** — if i18n lands, prefer server-side templates.

### Island boundary

Use an island when interaction is inherently client-side (dialog, toast DOM, attaching a request header). Prefer HTMX when the server can return the next HTML fragment. Do not move list/table/form flows into islands “for speed.”

### Admin shell

The browser UI is a Bootstrap 5 admin shell (navbar, sidebar, footer, colour mode / palette / profile). Vendored CSS and JS live under `app/web/static/` (`vendor/bootstrap`, `vendor/bootstrap-icons`, `vendor/chart.js`, plus `css/` and `js/`). There is no Sass or npm build.

`templates/layout.html` is the shell. Shared pieces are `partials/navbar.html`, `partials/sidebar.html`, and `partials/footer.html`. Operational pages extend the layout and replace only `{% block content %}`. Header and sidebar specimen pages keep their own chrome (`templates/gallery/`) because that chrome is the specimen; they still include the shared sidebar or navbar.

The sidebar has two groups. **App** is the product: Dashboard, Books, Search books, and Staff (`/ui/admin/users`, admin only). **Samples** is the Bootstrap page set kept as UI copy sources (users, forms, tables, components, cheatsheet, settings, blank, headers, sidebars). Sample pages are not the product. The Users sample stays separate from Staff. Move a link from Samples to App when that page starts reading or writing application data.

`app/web/static/css/admin.css` stays the shell layout file. `app/web/static/css/app.css` is the HTMX indicator plus the books table sort caret. `app/web/static/js/admin.js` is the shell (theme, palette, profile, hash nav, form validation), with hash highlighting keyed off the `/ui/...` path instead of `*.html` filenames. `app/web/static/js/app.js` is the HTMX island (Bootstrap confirm modal, toasts, CSRF header, page-size select).

To add a page: copy `templates/pages/blank.html`, add a row to `SHELL_PAGES` in `app/web/pages_routes.py`, and add a sidebar link in `partials/sidebar.html` under App or Samples with an `active` key. Do not introduce a client-side HTML include loader.

## Product shape

| Surface | Role |
|---------|------|
| SQLite + session/CSRF + HTMX UI + protected books JSON API | Primary path — fork and grow this |
| `/items` (in-memory) | Minimal teaching CRUD — no auth, no UI |
| `/db-items` (MongoDB) | Optional NoSQL demo — removable |

Do not add auth, HTMX, or shared abstractions to the memory/Mongo demos unless the point is to teach that idea. Keep demos thin on purpose. `/items` and `/db-items` teach storage. Delete them when a fork does not need them.

Books is the reference domain in this repo, not a requirement of every fork. Copy `app/routes/books.py`, `app/db/books.py`, and `app/web/books_routes.py` for the next entity, then replace books. Keep the URL split (`/api`, `/auth`, `/ui`), session/CSRF, Bearer tokens, roles, and the list contract (`page`, `size`, allowlisted `ordering`, `innerHTML` swaps). Demo routes keep the thin **Item** naming so they are not a second product.

## Roles

Three hierarchical roles on `users.role`:

| Role | Capabilities |
|------|----------------|
| `viewer` | Read books (UI + API GET) |
| `editor` | Create / update / delete books |
| `admin` | Editor powers + `/ui/admin/users` (list users, change roles) |

Enforcement is always on the server (`require_user` / `require_editor` / `require_admin` and HTML variants). Templates hide buttons; never trust the UI alone.

The seeded demo user is an **admin** (`DEMO_USERNAME` / `DEMO_PASSWORD`).

Startup only ensures that admin when `users` is empty. Richer demo data (sample `viewer` / `editor` accounts and books) is opt-in via `python -m app.seed` / `make seed` — idempotent (skips existing usernames). The sample catalog is about 100 well-known titles so page size and column sorting are easy to exercise. Re-running the seed inserts missing titles and refreshes the shelf category on titles it already knows. Other books are left alone.

## Code style (primary path)

Write primary-path code like the SQL and web layers:

- Thin route handlers: validate → call a helper → map to the response model.
- SQL in small modules (`app/db/…`, `app/auth/users.py`) with parameterized queries.
- Schema in `app/db/schema.sql`.
- Pydantic models are request/response schemas only, not persistence objects.
- Prefer FastAPI dependencies for auth over ad-hoc checks in every handler.

Reference implementations: `app/routes/books.py`, `app/db/books.py`, `app/web/books_routes.py`.

The in-memory and Mongo routes may stay more verbose (logic in the handler, broad try/except). That style is for demos only — do not copy it into the primary path.

## URL layout

Path indicates the client. Do not serve HTML under `/api`, and do not issue API tokens from the HTML `/auth` routes.

| Prefix | Client | Auth | Response |
|--------|--------|------|----------|
| `/api/...` | Machines (curl, Swagger, services) | Bearer (session also allowed where useful) | JSON |
| `/auth/...` | Browsers | Session cookie + CSRF | HTML (forms, redirects) |
| `/ui/...` | Browsers and HTMX | Session + CSRF on mutations | HTML pages and fragments |
| `/items`, `/db-items` | Teaching demos | None | JSON |
| `/`, `/health`, `/docs` | Ops / docs | — | unchanged |

**Browser auth routes:** `GET/POST /auth/login`, `POST /auth/logout` — establish or clear a session. Logout is POST-only with CSRF (no GET logout). No token issuance here.

**API auth routes:** `POST /api/auth/token` (issue), `DELETE /api/auth/token` (revoke current Bearer), `GET /api/auth/me` (introspect, includes `role`).

**HTMX:** pages and partials share the `/ui/...` prefix (same router). Do not add a separate `/htmx` prefix. Use `templates/` for full pages and `templates/partials/` for fragments.

Primary mounts:

| Surface | Path |
|---------|------|
| UI list / HTMX | `/ui/books` (full page or partial via `HX-Request`) |
| Advanced search | `/ui/books/search` (filters outside swap target) |
| Staff | `/ui/admin/users` (admin only) |
| JSON API | `/api/books` (reads: login; writes: editor+; filter query params) |
| Root | `/` → `/ui/dashboard` |

Demos remain at `/items` and `/db-items`.

### Books fields and N+1

Books include scalars (`category`, `isbn`, `page_count`, `available`) and `added_by_user_id` → `users`. List/get **LEFT JOIN** users so `added_by_username` is loaded in the same query — do not resolve the adder with a per-row `get_user_by_id` (classic N+1).

### HTMX patterns in use

See **UI architecture** for the HTML-first contract. Patterns below are what this app actually ships (Bootstrap shell + `app.js`). Do not add Idiomorph, `hx-boost` shells, or OOB toasts unless they land in code and this file in the same change.

- **`HX-Request` dual response** — one list route returns the full page or `partials/books_table.html`.
- **Search** — `q` on title/author/ISBN with debounce + `hx-push-url`. Keep the search/filter form **outside** the HTMX swap target so inputs are not replaced (focus stays while typing).
- **Advanced filters** — `/ui/books/search`: selects + debounced text update live; year inputs update on `change`/explicit Apply (avoid mid-typing requests). Active filter chips render inside the results partial. Delete keeps filter query params via `return_to`.
- **Pagination and sort** — URL is the source of truth: `page`, `size` (`10`, `25`, `50`, `100`; default 10), and `ordering` (allowlisted column, prefix `-` for descending; default `title`). Sort links and the page-size control swap `#books-panel` with `innerHTML` and `hx-push-url`. Filter forms keep a hidden `ordering` so a search does not drop the sort. Unknown `ordering` values fall back to the default. Same contract on `/api/books`. Swaps stay `innerHTML`; do not add Idiomorph for this.
- **Indicator** — shared `#books-indicator` via `hx-indicator` (search, pagination, sort, create). CSS-only spinner; HTMX toggles `.htmx-request` / opacity. Keep the indicator outside the swap target.
- Progressive enhancement: pagination links keep usable `href`s.
- **Confirm modal** — Bootstrap modal + small JS (`app/web/static/js/app.js`); delete buttons use `hx-trigger="confirmed-delete"` after the user confirms (no `window.confirm`).
- **Toasts** — Bootstrap toasts; server sets `HX-Trigger: {"showToast": {...}}` (e.g. after delete).

## Authentication

Teaching overview (cookies, CSRF, Bearer): [`auth.md`](auth.md).

One user store; two client mechanisms:

1. **Browsers / HTMX** — signed session cookie. Mutating HTML/HTMX requests require CSRF (`require_user_html`, `verify_csrf`).
2. **Machine clients** — opaque Bearer token from `POST /api/auth/token` (username/password). Store tokens in SQLite so revocation is deleting a row. Do not default to JWT unless this document is updated to say so.
3. **Protected JSON routes** — `require_user` accepts a valid session **or** a valid Bearer token. If the client uses the **session cookie** on a mutating method (`POST`/`PUT`/`PATCH`/`DELETE`), CSRF is required (`X-CSRF-Token` header or form field). **Bearer requests skip CSRF.** Role gates: `require_editor`, `require_admin`.
4. **Same-origin JS calling `/api`** — either send the session cookie with `credentials: "include"` **and** `X-CSRF-Token` (from the page meta tag), or use a Bearer token. Prefer Bearer for non-HTML clients; session+CSRF is fine for page scripts.
5. **Swagger `/docs`** — use HTTP Bearer for `/api` routes. Cookie login is for the UI, not the main docs Authorize flow.

In-memory and Mongo demos remain unauthenticated unless that changes deliberately.

Implemented: session + CSRF for the UI and for session-authenticated `/api` writes; `POST/DELETE /api/auth/token` + opaque tokens in `api_tokens`; `require_user` accepts Bearer or session; Swagger shows HTTP Bearer via `HTTPBearer` on API deps.

## Logging

Stdlib `logging` to **stdout** (Docker/12-factor). No log files, Loguru, or structlog.

| Setting | Role |
|---------|------|
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`. Default `INFO`. How chatty the app is. |
| `ENVIRONMENT` | `production` → one JSON object per line (for a log shipper). Anything else → human-readable text. |
| `DEBUG` | When true, dump masked settings at startup (`log_config_values`). Independent of `LOG_LEVEL`. |

Configure once in `app/core/logging.py` (`setup_logging` from the lifespan). Use `logging.getLogger(__name__)` in modules. `LOG_LEVEL` applies to the `app` logger (and uvicorn). The root logger stays at INFO so third-party DEBUG does not flood stdout. `pymongo` / `motor` / `httpx` / `httpcore` / `urllib3` are pinned to WARNING (PyMongo otherwise logs a topology heartbeat every ~10s at DEBUG). Uvicorn access logs stay at INFO even if `LOG_LEVEL` is higher.

Do not log passwords, session cookies, Bearer tokens, or CSRF secrets. Examples: failed HTML login and failed `POST /api/auth/token` log `username=` only.

## Schema / local SQLite

`CREATE TABLE IF NOT EXISTS` does not migrate existing databases. Startup runs a small additive migrate for new `books` columns when missing; for larger shape changes, delete local `data/*.db` (and test DBs) and restart. Prefer recreate / tiny ALTER helpers over Alembic.

## Non-negotiables

- **Async-first** on the request path (async handlers, aiosqlite, Motor). Avoid new sync I/O in handlers. Sync `bcrypt` is an accepted exception; do not add more blocking work without noting it here.
- **No ORM** (no SQLAlchemy, SQLModel, Tortoise, etc.). SQL strings + parameters.
- **Removable modules** — Mongo, web UI, and demos must stay deletable via the README checklist pattern; do not entangle them into the primary path.
- **Document new patterns here** in the same change that introduces them.

## Patterns in use (primary path)

- Lifespan for connect / schema / seed / shutdown (not deprecated `@on_event`).
- Process-wide SQLite connection via `app/db/connection.py` (simple single-process setup; not a pool).
- Repository-style helpers return dicts (or simple structures); routes map to Pydantic.
- Separate dependencies for JSON vs HTML auth: `require_user` (Bearer or session) vs `require_user_html` + `LoginRequired` (session only); plus `require_editor` / `require_admin` (and HTML variants).
- Opaque API tokens hashed (SHA-256) in `api_tokens`; plaintext returned once from `POST /api/auth/token`.
- Settings via Pydantic Settings (`app/core/config.py`).
- Stdlib logging to stdout (`app/core/logging.py`); `LOG_LEVEL` env; JSON when `ENVIRONMENT=production`.
- Shared identity helpers in `app/auth/` (passwords, users, tokens, deps). HTTP routes live in `app/routes/` (JSON) and `app/web/` (HTML).
- **uv** for Python deps: `pyproject.toml` + committed `uv.lock`; Docker installs with `uv sync --frozen`. Do not reintroduce `requirements.txt` as a second source of truth. Target CPython **3.14** (`.python-version`, `requires-python`).

## Out of scope

Unless this document is updated first:

- ORMs and sync DB drivers for the primary path
- SPA frameworks, SPA routers, or a frontend build step (vanilla JS + HTMX + the Bootstrap admin shell)
- Alpine.js / React / Vue / Svelte (or similar) unless a concrete widget forces an island and this doc is updated
- HTMX out-of-band (`hx-swap-oob`) swaps, client-side i18n libraries
- OAuth2 / OIDC providers
- JWT as the default API token
- Django-style generic admin
- Loguru / structlog, log files inside the container, or a bundled log shipper
