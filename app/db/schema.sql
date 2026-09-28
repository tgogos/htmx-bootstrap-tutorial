CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer'
        CHECK (role IN ('viewer', 'editor', 'admin')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    notes TEXT,
    category TEXT NOT NULL DEFAULT 'other'
        CHECK (category IN (
            'fiction', 'nonfiction', 'scifi', 'fantasy',
            'mystery', 'biography', 'other'
        )),
    isbn TEXT,
    page_count INTEGER,
    available INTEGER NOT NULL DEFAULT 1 CHECK (available IN (0, 1)),
    added_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
-- category / available / added_by indexes are created in connection._migrate_books_columns
-- so older DBs (CREATE TABLE IF NOT EXISTS no-op) are not broken by INDEX-before-ALTER.

-- Opaque API tokens (store SHA-256 hash only; plaintext shown once at issue time)
CREATE TABLE IF NOT EXISTS api_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_api_tokens_user_id ON api_tokens(user_id);
