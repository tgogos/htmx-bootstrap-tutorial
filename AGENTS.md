# Agent notes

This repository is an HTMX 4 tutorial copied from the FastAPI + HTMX + Bootstrap boilerplate. Before changing it, read [`docs/ENGINEERING.md`](docs/ENGINEERING.md) and follow it.

## Must follow

- Teach from `/ui/tutorial`. Keep each new lesson to one interaction. The books table (`/ui/books`) is the advanced example for the end of the sequence, not the first page.
- HTMX is pinned to **4.0.0** (`app/web/static/js/htmx.min.js`). Use [four.htmx.org](https://four.htmx.org/docs). Do not reintroduce HTMX 2 event names (`htmx:configRequest`, `htmx:pushedIntoHistory`) or implicit attribute inheritance.
- Inherited boilerplate rules still apply: async request path, no ORM, Pydantic at the edge, uv, `/api` JSON vs `/auth` session vs `/ui` HTML, session + CSRF, Bearer tokens, roles, Bootstrap shell. Do not add Alpine, React, Vue, Svelte, SPA routing, or a frontend build step.
- An artificial delay belongs only on the tutorial card endpoint (`?delay=`) and on a one-letter tutorial search (`?slow=1`). The fragment must say the wait is artificial.
- Do not introduce new architectural patterns without updating `docs/ENGINEERING.md` in the same change.
- Python deps: **uv** only (`pyproject.toml` + `uv.lock`). Do not add `requirements.txt`.
- Logging: stdlib to stdout; `LOG_LEVEL` env; JSON when `ENVIRONMENT=production`. Do not log secrets. See `docs/ENGINEERING.md` § Logging.

## Scope

Only change what the task requires. Do not “improve” demo routes (`/items`, `/db-items`) toward the primary stack unless asked. Lessons 1–11 are the sequence. Do not add further lessons unless asked.
