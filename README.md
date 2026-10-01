# HTMX Bootstrap tutorial

A runnable tutorial for HTMX 4 on the FastAPI + Jinja + Bootstrap boilerplate. The books app, login, and roles are already here. The lessons start smaller than that table.

Browsers get HTML (Jinja + [Bootstrap 5.3](https://getbootstrap.com/) + [HTMX 4.0.0](https://four.htmx.org/docs)). Machines get `/api` with Bearer tokens.

Architecture: [`docs/ENGINEERING.md`](docs/ENGINEERING.md).  
Sessions, CSRF, and Bearer: [`docs/auth.md`](docs/auth.md).

## Start here

```bash
make dotenv
make upd
make seed     # books for the lessons
```

Open `/ui/tutorial` after logging in (`DEMO_USERNAME` / `DEMO_PASSWORD`, defaults `admin` / `admin123`). Lessons 1–9 are small interactions. Lesson 10 puts a page in the address bar. Lesson 11 walks the books table at `/ui/books`. Lesson 12 loads a few titles when a box scrolls into view. Lesson 13 fetches the server clock every two seconds. Lesson 14 puts the request on a form that hears a search box and a menu. Lesson 15 boosts a link and selects <code>#main</code>, so the shell stays. Patterns, at `/ui/patterns`, is a second sequence on the same books.

## Lessons

| | Page | Idea |
|--|------|------|
| 1 | `/ui/tutorial/1` | A normal link loads a full book page |
| 2 | `/ui/tutorial/2` | `hx-get` puts an HTML fragment into a target |
| 3 | `/ui/tutorial/3` | The same fetch, slowed on purpose, with `hx-indicator` |
| 4 | `/ui/tutorial/4` | `hx-swap` replaces the shelf or adds another card |
| 5 | `/ui/tutorial/5` | A category menu sends its value on `change` |
| 6 | `/ui/tutorial/6` | Search after a pause, and cancel a slower older request |
| 7 | `/ui/tutorial/7` | `hx-post` a form; a validation error comes back as HTML |
| 8 | `/ui/tutorial/8` | Edit with `hx-put`; delete only after confirmation |
| 9 | `/ui/tutorial/9` | `HX-Trigger` asks the small script to show a toast |
| 10 | `/ui/tutorial/10` | Page and sort links update the address; Back restores the full lesson |
| 11 | `/ui/tutorial/11` | The books URL as a full page or a fragment, then a walkthrough |
| 12 | `/ui/tutorial/12` | `hx-trigger="revealed"` loads the first five titles when the box reaches the screen |
| 13 | `/ui/tutorial/13` | `hx-trigger="every 2s"` fetches the server clock, then fetches it again |
| 14 | `/ui/tutorial/14` | `from:` on `hx-trigger` lets one form hear a search box and a menu |
| 15 | `/ui/tutorial/15` | `hx-boost` and `hx-select="#main"` swap the main region and leave the shell |

## Patterns

A second sequence after the lessons, at `/ui/patterns`. Same books, first eight titles. The books table does not gain checkboxes.

| | Page | Idea |
|--|------|------|
| 1 | `/ui/patterns/1` | A checkbox on each row. Nothing is sent |
| 2 | `/ui/patterns/2` | Checked ids are posted; `innerHTML` replaces the table |
| 3 | `/ui/patterns/3` | The same post, plus an out-of-band swap (`hx-swap-oob`) for the count outside the table |
| 4 | `/ui/patterns/4` | `innerMorph` keeps a check the new HTML does not set |
| 5 | `/ui/patterns/5` | Delete selected, after confirm, using the count fragment and the morph swap |
| 6 | `/ui/patterns/6` | Export selected; the bar polls and the finished fragment has no `every` |

## Primary path vs demos

| | Role |
|--|------|
| **Primary** | SQLite **books** · roles (viewer / editor / admin) · session + CSRF for `/ui` and `/auth` · Bearer (or session) for `/api/books` · Bootstrap admin shell + HTMX |
| **Demos** (thin, removable) | `/items` in-memory CRUD · `/db-items` MongoDB CRUD |

## Quick start

**Requires:** Docker Compose. Make is optional. Dependencies are managed with [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`).

```bash
make dotenv   # .env.example → .env
make upd      # build + start (detached)

# http://localhost:8000              → /ui/dashboard (login first)
# http://localhost:8000/auth/login
# http://localhost:8000/ui/books     → books CRUD
# http://localhost:8000/docs         → OpenAPI (JSON API only)
```

Demo user (seeded when `users` is empty) is an **admin**: `DEMO_USERNAME` / `DEMO_PASSWORD` (defaults `admin` / `admin123`). Change these and **`SECRET_KEY`** before any shared deploy.

```bash
make seed     # optional viewer + editor users and sample books
make test
make down
```

### Local development with uv (optional)

```bash
uv sync --all-groups
uv run fastapi dev app/main.py --port 8000 --host 0.0.0.0
uv run pytest
```

## UI

The shell is `app/ui/templates/layout.html` (navbar, sidebar, footer). Sample pages keep their own routes:

| Page | Path |
|------|------|
| Dashboard | `/ui/dashboard` |
| Users, Forms, Tables | `/ui/users`, `/ui/forms`, `/ui/tables` |
| Components, Cheatsheet, Palette lab | `/ui/components`, `/ui/cheatsheet`, `/ui/palette-lab` |
| Settings, Blank, 404 | `/ui/settings`, `/ui/blank`, `/ui/404` |
| Header specimens | `/ui/headers/simple` (and centered, buttons, dark, account, product, double, icons) |
| Sidebar specimens | `/ui/sidebars/dark` (and light, icons, collapsible, list-group) |
| Sign in | `/auth/login` |

Working data pages use the same shell:

| Page | Path |
|------|------|
| Books | `/ui/books` |
| Search books | `/ui/books/search` |
| Staff (admin) | `/ui/admin/users` |

The sidebar is split into **App** (the product) and **Samples** (the original Bootstrap pages). To add a page, copy `app/ui/templates/pages/blank.html`, register it in `SHELL_PAGES` in `app/ui/pages_routes.py`, and add a sidebar link under the matching group in `app/ui/templates/partials/sidebar.html`.

## Auth in brief

- **Browser / HTMX:** cookie session + CSRF on mutating HTML (`/auth`, `/ui`).
- **API:** Bearer via `POST /api/auth/token`, or session cookie. Session writes to `/api` need `X-CSRF-Token`. Bearer skips CSRF.

```bash
curl -s -X POST http://localhost:8000/api/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
```

## Layout

```
app/
  auth/     # passwords, users, tokens, deps
  db/       # SQLite connection + schema (primary)
  routes/   # JSON API (/api/..., demos)
  ui/       # HTML/HTMX templates + Bootstrap static
  models/   # Pydantic schemas
  core/     # settings + logging
docs/
pyproject.toml
uv.lock
```

## License

MIT — see [LICENSE](LICENSE). Third-party notices for vendored front-end files are in [LICENSES.md](LICENSES.md).
