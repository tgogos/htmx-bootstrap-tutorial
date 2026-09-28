# Auth: sessions, CSRF, Bearer tokens, and roles

How authentication works in this project, in plain language. For hard rules when changing code, see [`ENGINEERING.md`](ENGINEERING.md). For a short operator summary, see the README.

## Two ways to prove who you are

One user table in SQLite; two client mechanisms:

| | Session cookie | Bearer token |
|--|----------------|--------------|
| Typical client | Browser + HTMX UI | curl, Swagger, mobile, scripts |
| How it is sent | Browser attaches the cookie automatically | Client sets `Authorization: Bearer …` |
| Where it lives | Browser cookie jar | String returned once from `/api/auth/token` |
| CSRF on writes? | Yes | No |

## Roles

| Role | Books read | Books write | Admin users UI |
|------|------------|-------------|----------------|
| `viewer` | yes | no | no |
| `editor` | yes | yes | no |
| `admin` | yes | yes | yes |

`GET /api/auth/me` returns `id`, `username`, and `role`. The demo seed user is `admin`.

Server deps: `require_user` / `require_editor` / `require_admin` (JSON) and `*_html` variants (session UI). Templates may hide controls; routes still enforce.

## Browser login (session)

1. User submits username/password on `/auth/login`.
2. Server verifies the password and stores `user_id` in a **signed session**.
3. Server responds with `Set-Cookie`; the browser stores it.
4. Later requests to this site include that cookie automatically.
5. Server reads the session → knows the user → serves `/ui/...` or accepts cookie auth on `/api/...`.

You do not manually attach the cookie. That convenience is why CSRF protection exists.

## CSRF (cross-site request forgery)

**Idea:** a malicious site can cause the browser to send a request to *your* app while the user is logged in. The browser will include your session cookie. Without an extra check, your server may treat that as a real user action (create/delete data, etc.).

**Defense used here:** the server keeps a random CSRF secret in the session and embeds it in HTML (hidden form field and/or `<meta name="csrf-token">`). Mutating requests (`POST` / `PUT` / `PATCH` / `DELETE`) must send that secret back:

- HTML forms: `csrf_token` field
- `fetch` / XHR: `X-CSRF-Token` header

A page on another origin cannot read your HTML (same-origin policy), so it cannot forge the correct CSRF value even though it might trigger a request that carries the cookie.

### Where CSRF is enforced

- Mutating `/auth` and `/ui` routes (HTML/HTMX).
- Mutating `/api` routes when the client authenticates with the **session cookie** (`require_user` / role deps that call it).
- **Not** required when the client sends a valid **Bearer** token.

## Bearer tokens (API)

1. Client calls `POST /api/auth/token` with username/password.
2. Server creates a long random string, stores only a **SHA-256 hash** in `api_tokens`, returns the plaintext once.
3. Client sends `Authorization: Bearer <token>` on later requests.
4. `DELETE /api/auth/token` with that Bearer header deletes the row (revoke).

Browsers do not attach `Authorization` automatically to cross-site requests the way they do cookies, so classic cookie CSRF does not apply. (XSS on *your* pages is a different risk: malicious script on your origin could read tokens or CSRF secrets.)

Swagger `/docs` is set up for HTTP Bearer: obtain a token, then use **Authorize**.

## Same-origin JavaScript calling `/api`

Either:

```js
// Session + CSRF (page already logged in via /auth)
fetch("/api/books/", {
  method: "POST",
  credentials: "include",
  headers: {
    "Content-Type": "application/json",
    "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content,
  },
  body: JSON.stringify({
    title: "Example",
    author: "Ada",
    year: 2020,
    notes: null,
  }),
});
```

Or use a Bearer token in `Authorization` (no CSRF header). Prefer Bearer for non-HTML clients; session + CSRF is fine for scripts on your own pages.

## Headers and status codes (cheat sheet)

| Thing | Meaning |
|-------|---------|
| `Cookie` | Browser sending the session |
| `Set-Cookie` | Server asking the browser to store a cookie |
| `Authorization: Bearer …` | Explicit API token |
| `X-CSRF-Token` | CSRF secret for cookie-authenticated writes |
| **401** | Not authenticated |
| **403** | Forbidden (bad/missing CSRF, or insufficient role) |
| **303** | Redirect (e.g. anonymous UI → `/auth/login`) |

## How this maps to URLs

```
/auth/login, /auth/logout     Browser session (HTML); CSRF on POST
/ui/books                     HTMX books UI; session + CSRF on mutations
/ui/admin/users               Admin-only staff page
POST   /api/auth/token        Issue Bearer token
DELETE /api/auth/token        Revoke current Bearer token
GET    /api/auth/me           Current user + role (Bearer or session)
/api/books/...                JSON CRUD; reads: login; writes: editor+ (Bearer OR session+CSRF)
/items, /db-items             Demos — no auth
```

Relevant code: `app/auth/deps.py`, `app/auth/tokens.py`, `app/auth/users.py`, `app/web/auth_routes.py`, `app/routes/api_auth.py`.
