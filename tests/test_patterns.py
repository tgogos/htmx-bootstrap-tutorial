"""Patterns pages: select, mark, count, morph, delete, export."""

from fastapi.testclient import TestClient

from tests.conftest import create_user_sync, login_as, session_csrf_headers

API_BOOKS = "/api/books"


def _create_book(auth_client: TestClient, title: str, *, available: bool = True) -> str:
    headers = session_csrf_headers(auth_client)
    created = auth_client.post(
        f"{API_BOOKS}/",
        json={
            "title": title,
            "author": "Pattern",
            "year": 2001,
            "category": "other",
            "available": available,
        },
        headers=headers,
    )
    assert created.status_code == 201
    return created.json()["id"]


class TestPatterns:
    def test_pages_require_login(self, client: TestClient):
        for path in (
            "/ui/patterns",
            "/ui/patterns/1",
            "/ui/patterns/6",
            "/ui/patterns/6/export",
        ):
            response = client.get(path, follow_redirects=False)
            assert response.status_code == 303
            assert response.headers["location"] == "/auth/login"

    def test_index_lists_the_six_pages(self, auth_client: TestClient):
        page = auth_client.get("/ui/patterns")
        assert page.status_code == 200
        assert 'href="/ui/patterns"' in page.text
        assert ">Patterns<" in page.text
        for n in range(1, 7):
            assert f'href="/ui/patterns/{n}"' in page.text
        books = auth_client.get("/ui/books")
        assert "Mark available" not in books.text
        assert 'name="book_id"' not in books.text

    def test_select_does_not_post(self, auth_client: TestClient):
        book_id = _create_book(auth_client, "Pattern Select")
        page = auth_client.get("/ui/patterns/1")
        assert page.status_code == 200
        assert f'value="{book_id}"' in page.text
        assert 'hx-post="' not in page.text
        assert 'id="available-count"' in page.text
        assert "<strong>1</strong> available" in page.text

    def test_mark_replaces_the_table_and_leaves_the_count(self, auth_client: TestClient):
        book_id = _create_book(auth_client, "Pattern Mark")
        page = auth_client.get("/ui/patterns/2")
        assert 'hx-swap="innerHTML"' in page.text
        assert 'hx-post="/ui/patterns/2/mark"' in page.text
        headers = session_csrf_headers(auth_client)
        marked = auth_client.post(
            "/ui/patterns/2/mark",
            data={"book_id": book_id, "available": "0"},
            headers=headers,
        )
        assert marked.status_code == 200
        assert "hx-swap-oob" not in marked.text
        assert "text-bg-secondary" in marked.text
        assert "Select at least one book." in auth_client.post(
            "/ui/patterns/2/mark",
            data={"available": "1"},
            headers=headers,
        ).text

    def test_count_updates_out_of_band(self, auth_client: TestClient):
        book_id = _create_book(auth_client, "Pattern Count")
        headers = session_csrf_headers(auth_client)
        marked = auth_client.post(
            "/ui/patterns/3/mark",
            data={"book_id": book_id, "available": "0"},
            headers=headers,
        )
        assert marked.status_code == 200
        assert 'hx-swap-oob="outerHTML"' in marked.text
        assert "<strong>0</strong> available" in marked.text

    def test_refresh_uses_inner_morph(self, auth_client: TestClient):
        _create_book(auth_client, "Pattern Morph")
        page = auth_client.get("/ui/patterns/4")
        assert 'hx-swap="innerMorph"' in page.text
        refreshed = auth_client.get("/ui/patterns/4/table")
        assert refreshed.status_code == 200
        assert "Pattern Morph" in refreshed.text
        assert 'hx-swap="innerMorph"' in refreshed.text

    def test_delete_removes_the_book_and_the_count(self, auth_client: TestClient):
        book_id = _create_book(auth_client, "Pattern Delete")
        headers = session_csrf_headers(auth_client)
        deleted = auth_client.post(
            "/ui/patterns/5/delete",
            data={"book_id": book_id},
            headers=headers,
        )
        assert deleted.status_code == 200
        assert "Pattern Delete" not in deleted.text
        assert 'hx-swap-oob="outerHTML"' in deleted.text
        assert "<strong>0</strong> available" in deleted.text
        missing = auth_client.get(f"{API_BOOKS}/{book_id}")
        assert missing.status_code == 404

    def test_export_advances_then_stops(self, auth_client: TestClient):
        book_id = _create_book(auth_client, "Pattern Export")
        idle = auth_client.get("/ui/patterns/6/export")
        assert "Nothing is exporting." in idle.text
        assert "every 1s" not in idle.text
        headers = session_csrf_headers(auth_client)
        started = auth_client.post(
            "/ui/patterns/6/export",
            data={"book_id": book_id},
            headers=headers,
        )
        assert started.status_code == 200
        assert "every 1s" in started.text
        assert "0%" in started.text
        step = auth_client.get("/ui/patterns/6/export")
        assert "25%" in step.text
        assert "every 1s" in step.text
        last = step
        for _ in range(3):
            last = auth_client.get("/ui/patterns/6/export")
        assert "Export ready: Pattern Export." in last.text
        assert "every 1s" not in last.text
        assert "does not wait" in last.text

    def test_viewer_can_read_but_not_mark(self, client: TestClient):
        create_user_sync("patternviewer", "viewerpass", role="viewer")
        login_as(client, "patternviewer", "viewerpass")
        page = client.get("/ui/patterns/2")
        assert page.status_code == 200
        assert "An editor can change these books." in page.text
        assert ">Mark available</button>" not in page.text
        headers = session_csrf_headers(client)
        denied = client.post(
            "/ui/patterns/2/mark",
            data={"available": "1"},
            headers=headers,
        )
        assert denied.status_code == 403

    def test_unknown_pattern_is_404(self, auth_client: TestClient):
        assert auth_client.get("/ui/patterns/7").status_code == 404
