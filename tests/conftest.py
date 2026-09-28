"""Pytest fixtures.

Sets test env vars before importing the app so Settings pick them up.
Requires MongoDB (same as existing suite; use `make test` via compose).
"""
import os
import sqlite3
from pathlib import Path

# Must run before app/core.config import side effects
_TEST_DB = Path(__file__).resolve().parent / ".test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest"
os.environ["DEBUG"] = "false"
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("DEMO_USERNAME", "admin")
os.environ.setdefault("DEMO_PASSWORD", "admin123")
os.environ.setdefault("MONGO_HOST", "mongodb")

import pytest
from fastapi.testclient import TestClient

from app.auth.passwords import hash_password
from app.main import app
from app.routes.items import items_storage


@pytest.fixture
def client():
    """Test client with lifespan (Mongo + SQLite startup)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clear_items_storage():
    """Clear in-memory items between tests."""
    items_storage.clear()
    yield
    items_storage.clear()


@pytest.fixture(autouse=True)
def clear_books_and_extra_users(request):
    """Clear books and non-demo users between tests; keep demo admin."""
    if request.node.get_closest_marker("no_client"):
        yield
        return

    request.getfixturevalue("client")
    db_path = Path(os.environ["DATABASE_URL"].removeprefix("sqlite:///"))
    demo = os.environ["DEMO_USERNAME"]

    def _reset():
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM books")
        conn.execute("DELETE FROM api_tokens")
        conn.execute("DELETE FROM users WHERE username != ?", (demo,))
        conn.execute(
            "UPDATE users SET role = 'admin' WHERE username = ?",
            (demo,),
        )
        conn.commit()
        conn.close()

    _reset()
    yield
    _reset()


@pytest.fixture
def sample_item_data():
    """In-memory / Mongo demo item payload."""
    return {
        "name": "Test Item",
        "description": "A test item for testing purposes",
    }


@pytest.fixture
def sample_item_update_data():
    return {
        "name": "Updated Test Item",
        "description": "An updated test item",
    }


@pytest.fixture
def sample_book_data():
    return {
        "title": "Test Book",
        "author": "Ada Lovelace",
        "year": 1842,
        "notes": "A test book",
        "category": "biography",
        "isbn": "978-0000000001",
        "page_count": 320,
        "available": True,
    }


@pytest.fixture
def sample_book_update_data():
    return {
        "title": "Updated Book",
        "author": "Grace Hopper",
        "year": 1952,
        "notes": "Updated notes",
        "category": "scifi",
        "isbn": "978-0000000002",
        "page_count": 400,
        "available": False,
    }


@pytest.fixture
def auth_client(client: TestClient):
    """Client logged in as the demo admin (session cookie)."""
    login_page = client.get("/auth/login")
    assert login_page.status_code == 200
    html = login_page.text
    marker = 'name="csrf_token" value="'
    assert marker in html
    csrf = html.split(marker, 1)[1].split('"', 1)[0]

    response = client.post(
        "/auth/login",
        data={
            "username": os.environ["DEMO_USERNAME"],
            "password": os.environ["DEMO_PASSWORD"],
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    return client


def session_csrf_headers(client: TestClient) -> dict[str, str]:
    """CSRF header for session-authenticated JSON/API calls (from UI meta tag)."""
    page = client.get("/ui/books")
    assert page.status_code == 200
    marker = 'name="csrf-token" content="'
    assert marker in page.text
    token = page.text.split(marker, 1)[1].split('"', 1)[0]
    return {"X-CSRF-Token": token}


def create_user_sync(username: str, password: str, role: str = "viewer") -> None:
    """Insert a user via sync sqlite (tests)."""
    db_path = Path(os.environ["DATABASE_URL"].removeprefix("sqlite:///"))
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, hash_password(password), role),
    )
    conn.commit()
    conn.close()


def login_as(client: TestClient, username: str, password: str) -> TestClient:
    """Replace session by logging in as the given user."""
    client.cookies.clear()
    login_page = client.get("/auth/login")
    csrf = login_page.text.split('name="csrf_token" value="', 1)[1].split('"', 1)[0]
    response = client.post(
        "/auth/login",
        data={
            "username": username,
            "password": password,
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    return client
