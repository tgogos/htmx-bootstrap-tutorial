"""Tests for /api/books, roles, API tokens, and browser auth."""

import logging
import os

from fastapi.testclient import TestClient

from tests.conftest import create_user_sync, login_as, session_csrf_headers

API_BOOKS = "/api/books"


class TestBooksApi:
    def test_list_requires_auth(self, client: TestClient):
        assert client.get(f"{API_BOOKS}/").status_code == 401

    def test_list_empty(self, auth_client: TestClient):
        response = auth_client.get(f"{API_BOOKS}/")
        assert response.status_code == 200
        body = response.json()
        assert body["total_count"] == 0
        assert body["items"] == []

    def test_create_requires_auth(self, client: TestClient, sample_book_data: dict):
        response = client.post(f"{API_BOOKS}/", json=sample_book_data)
        assert response.status_code == 401

    def test_session_write_requires_csrf(
        self, auth_client: TestClient, sample_book_data: dict
    ):
        response = auth_client.post(f"{API_BOOKS}/", json=sample_book_data)
        assert response.status_code == 403

    def test_crud_flow_authenticated(
        self,
        auth_client: TestClient,
        sample_book_data: dict,
        sample_book_update_data: dict,
    ):
        headers = session_csrf_headers(auth_client)

        create = auth_client.post(
            f"{API_BOOKS}/", json=sample_book_data, headers=headers
        )
        assert create.status_code == 201
        book = create.json()
        book_id = book["id"]
        assert book["title"] == sample_book_data["title"]
        assert book["category"] == "biography"
        assert book["added_by_username"] == os.environ["DEMO_USERNAME"]

        get_one = auth_client.get(f"{API_BOOKS}/{book_id}")
        assert get_one.status_code == 200
        assert get_one.json()["id"] == book_id
        assert get_one.json()["added_by_username"] == os.environ["DEMO_USERNAME"]

        update = auth_client.put(
            f"{API_BOOKS}/{book_id}",
            json=sample_book_update_data,
            headers=headers,
        )
        assert update.status_code == 200
        assert update.json()["title"] == sample_book_update_data["title"]

        search = auth_client.get(
            f"{API_BOOKS}/",
            params={"q": sample_book_update_data["author"]},
        )
        assert search.status_code == 200
        assert search.json()["total_count"] >= 1

        delete = auth_client.delete(f"{API_BOOKS}/{book_id}", headers=headers)
        assert delete.status_code == 204

        missing = auth_client.get(f"{API_BOOKS}/{book_id}")
        assert missing.status_code == 404

    def test_list_filters_and_join_username(
        self, auth_client: TestClient, sample_book_data: dict
    ):
        headers = session_csrf_headers(auth_client)
        other = {
            **sample_book_data,
            "title": "Other Book",
            "category": "mystery",
            "available": False,
            "isbn": "978-9999999999",
        }
        assert (
            auth_client.post(
                f"{API_BOOKS}/", json=sample_book_data, headers=headers
            ).status_code
            == 201
        )
        assert (
            auth_client.post(f"{API_BOOKS}/", json=other, headers=headers).status_code
            == 201
        )

        by_cat = auth_client.get(f"{API_BOOKS}/", params={"category": "mystery"})
        assert by_cat.status_code == 200
        assert by_cat.json()["total_count"] == 1
        assert by_cat.json()["items"][0]["title"] == "Other Book"
        assert by_cat.json()["items"][0]["added_by_username"]

        by_avail = auth_client.get(f"{API_BOOKS}/", params={"available": "false"})
        assert by_avail.status_code == 200
        assert by_avail.json()["total_count"] == 1

        by_isbn = auth_client.get(f"{API_BOOKS}/", params={"q": "978-9999999999"})
        assert by_isbn.status_code == 200
        assert by_isbn.json()["total_count"] == 1

    def test_list_ordering(self, auth_client: TestClient):
        headers = session_csrf_headers(auth_client)
        for title, year in (("Zebra Tales", 1999), ("Aardvark Tales", 2001)):
            assert (
                auth_client.post(
                    f"{API_BOOKS}/",
                    json={"title": title, "author": "Sorter", "year": year},
                    headers=headers,
                ).status_code
                == 201
            )

        asc = auth_client.get(f"{API_BOOKS}/", params={"ordering": "title", "q": "Tales"})
        assert [item["title"] for item in asc.json()["items"]] == [
            "Aardvark Tales",
            "Zebra Tales",
        ]
        desc = auth_client.get(
            f"{API_BOOKS}/", params={"ordering": "-title", "q": "Tales"}
        )
        assert [item["title"] for item in desc.json()["items"]] == [
            "Zebra Tales",
            "Aardvark Tales",
        ]
        unknown = auth_client.get(
            f"{API_BOOKS}/", params={"ordering": "drop table", "q": "Tales"}
        )
        assert unknown.status_code == 200
        assert unknown.json()["items"][0]["title"] == "Aardvark Tales"

        by_year = auth_client.get(
            f"{API_BOOKS}/", params={"ordering": "-year", "q": "Tales"}
        )
        assert [item["title"] for item in by_year.json()["items"]] == [
            "Aardvark Tales",
            "Zebra Tales",
        ]


class TestRoles:
    def test_viewer_cannot_write(self, client: TestClient, sample_book_data: dict):
        create_user_sync("viewer1", "viewerpass", role="viewer")
        login_as(client, "viewer1", "viewerpass")
        headers = session_csrf_headers(client)
        response = client.post(f"{API_BOOKS}/", json=sample_book_data, headers=headers)
        assert response.status_code == 403

        listed = client.get(f"{API_BOOKS}/")
        assert listed.status_code == 200

    def test_editor_can_write(self, client: TestClient, sample_book_data: dict):
        create_user_sync("editor1", "editorpass", role="editor")
        login_as(client, "editor1", "editorpass")
        headers = session_csrf_headers(client)
        create = client.post(f"{API_BOOKS}/", json=sample_book_data, headers=headers)
        assert create.status_code == 201

    def test_admin_users_forbidden_for_non_admin(self, client: TestClient):
        create_user_sync("editor2", "editorpass", role="editor")
        login_as(client, "editor2", "editorpass")
        assert client.get("/ui/admin/users").status_code == 403

    def test_admin_users_ok_for_admin(self, auth_client: TestClient):
        response = auth_client.get("/ui/admin/users")
        assert response.status_code == 200
        assert "Users" in response.text


class TestApiAuth:
    def test_token_and_bearer_crud(
        self, client: TestClient, sample_book_data: dict
    ):
        bad = client.post(
            "/api/auth/token",
            json={"username": "nope", "password": "wrong"},
        )
        assert bad.status_code == 401

        token_resp = client.post(
            "/api/auth/token",
            json={
                "username": os.environ["DEMO_USERNAME"],
                "password": os.environ["DEMO_PASSWORD"],
            },
        )
        assert token_resp.status_code == 200
        token = token_resp.json()["access_token"]
        assert token_resp.json()["token_type"] == "bearer"
        headers = {"Authorization": f"Bearer {token}"}

        me = client.get("/api/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["username"] == os.environ["DEMO_USERNAME"]
        assert me.json()["role"] == "admin"

        create = client.post(f"{API_BOOKS}/", json=sample_book_data, headers=headers)
        assert create.status_code == 201
        book_id = create.json()["id"]

        delete = client.delete(f"{API_BOOKS}/{book_id}", headers=headers)
        assert delete.status_code == 204

        revoke = client.delete("/api/auth/token", headers=headers)
        assert revoke.status_code == 204

        me_after = client.get("/api/auth/me", headers=headers)
        assert me_after.status_code == 401

    def test_invalid_bearer_rejected(self, client: TestClient, sample_book_data: dict):
        response = client.post(
            f"{API_BOOKS}/",
            json=sample_book_data,
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        assert response.status_code == 401

    def test_me_requires_auth(self, client: TestClient):
        assert client.get("/api/auth/me").status_code == 401

    def test_revoke_requires_bearer(self, client: TestClient):
        assert client.delete("/api/auth/token").status_code == 401


class TestAuthWeb:
    def test_login_page_ok(self, client: TestClient):
        response = client.get("/auth/login")
        assert response.status_code == 200
        assert "Log in" in response.text

    def test_books_ui_redirects_when_anonymous(self, client: TestClient):
        response = client.get("/ui/books", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/auth/login"

    def test_books_ui_ok_when_authenticated(self, auth_client: TestClient):
        response = auth_client.get("/ui/books")
        assert response.status_code == 200
        assert "Books" in response.text
        assert 'aria-sort="ascending"' in response.text
        assert "table-sort-link" in response.text
        assert 'aria-label="Rows per page"' in response.text
        assert "ordering=title" in response.text

        resorted = auth_client.get("/ui/books", params={"ordering": "-author"})
        assert 'aria-sort="descending"' in resorted.text
        assert "table-sort-link--desc" in resorted.text

    def test_dashboard_requires_login(self, client: TestClient):
        anonymous = client.get("/ui/dashboard", follow_redirects=False)
        assert anonymous.status_code == 303
        assert anonymous.headers["location"] == "/auth/login"

    def test_dashboard_shell(self, auth_client: TestClient):
        page = auth_client.get("/ui/dashboard")
        assert page.status_code == 200
        assert "Dashboard" in page.text
        assert 'href="/ui/books"' in page.text
        assert 'aria-label="App"' in page.text
        assert 'aria-label="Samples"' in page.text
        assert "bootstrap.min.css" in page.text

        users = auth_client.get("/ui/users")
        assert users.status_code == 200
        assert "Users" in users.text

        header = auth_client.get("/ui/headers/simple")
        assert header.status_code == 200
        assert "Simple header" in header.text

    def test_books_hx_partial_and_search(self, auth_client: TestClient):
        headers = session_csrf_headers(auth_client)
        auth_client.post(
            f"{API_BOOKS}/",
            json={
                "title": "Searchable Title",
                "author": "Author X",
                "year": 2001,
                "notes": None,
                "category": "fiction",
                "available": True,
            },
            headers=headers,
        )

        partial = auth_client.get(
            "/ui/books",
            headers={"HX-Request": "true"},
        )
        assert partial.status_code == 200
        assert "<table" in partial.text
        assert "<html" not in partial.text.lower()

        search = auth_client.get(
            "/ui/books",
            params={"q": "Searchable", "page": 1, "size": 10},
            headers={"HX-Request": "true"},
        )
        assert search.status_code == 200
        assert "Searchable Title" in search.text

        page = auth_client.get(
            "/ui/books",
            params={"page": 1, "size": 1},
        )
        assert page.status_code == 200

    def test_ui_includes_confirm_dialog_and_toast_region(
        self, auth_client: TestClient
    ):
        headers = session_csrf_headers(auth_client)
        auth_client.post(
            f"{API_BOOKS}/",
            json={"title": "Has Delete", "author": "A", "category": "other"},
            headers=headers,
        )
        page = auth_client.get("/ui/books")
        assert page.status_code == 200
        assert 'id="confirm-dialog"' in page.text
        assert 'id="toast-region"' in page.text
        assert 'hx-trigger="confirmed-delete"' in page.text

    def test_advanced_search_page(self, auth_client: TestClient):
        headers = session_csrf_headers(auth_client)
        auth_client.post(
            f"{API_BOOKS}/",
            json={
                "title": "Filter Me",
                "author": "Y",
                "category": "fantasy",
                "available": True,
                "year": 1999,
            },
            headers=headers,
        )
        page = auth_client.get("/ui/books/search")
        assert page.status_code == 200
        assert "Search books" in page.text
        assert 'name="category"' in page.text
        assert "Sci-Fi" in page.text or "Fantasy" in page.text

        filtered = auth_client.get(
            "/ui/books/search",
            params={"category": "fantasy", "available": "true"},
            headers={"HX-Request": "true"},
        )
        assert filtered.status_code == 200
        assert "Filter Me" in filtered.text
        assert "Active filters" in filtered.text
        assert "Fantasy" in filtered.text
        assert "<html" not in filtered.text.lower()

    def test_ui_delete_triggers_toast_header(self, auth_client: TestClient):
        headers = session_csrf_headers(auth_client)
        created = auth_client.post(
            f"{API_BOOKS}/",
            json={
                "title": "Toast Delete",
                "author": "Z",
                "category": "other",
            },
            headers=headers,
        )
        assert created.status_code == 201
        book_id = created.json()["id"]
        deleted = auth_client.delete(
            f"/ui/books/{book_id}?page=1&size=10&return_to=list",
            headers={**headers, "HX-Request": "true"},
        )
        assert deleted.status_code == 200
        assert "HX-Trigger" in deleted.headers
        assert "showToast" in deleted.headers["HX-Trigger"]
        assert "Book deleted" in deleted.headers["HX-Trigger"]

    def test_login_logout(self, client: TestClient):
        page = client.get("/auth/login")
        csrf = page.text.split('name="csrf_token" value="', 1)[1].split('"', 1)[0]
        login = client.post(
            "/auth/login",
            data={
                "username": os.environ["DEMO_USERNAME"],
                "password": os.environ["DEMO_PASSWORD"],
                "csrf_token": csrf,
            },
            follow_redirects=False,
        )
        assert login.status_code == 303

        ui = client.get("/ui/books")
        assert ui.status_code == 200
        csrf = ui.text.split('name="csrf_token" value="', 1)[1].split('"', 1)[0]

        logout = client.post(
            "/auth/logout",
            data={"csrf_token": csrf},
            follow_redirects=False,
        )
        assert logout.status_code == 303

        again = client.get("/ui/books", follow_redirects=False)
        assert again.status_code == 303

    def test_failed_login_logs_username_not_password(
        self, client: TestClient, caplog
    ):
        page = client.get("/auth/login")
        csrf = page.text.split('name="csrf_token" value="', 1)[1].split('"', 1)[0]
        secret = "super-secret-password-not-for-logs"
        with caplog.at_level(logging.WARNING, logger="app.web.auth_routes"):
            response = client.post(
                "/auth/login",
                data={
                    "username": "nobody",
                    "password": secret,
                    "csrf_token": csrf,
                },
                follow_redirects=False,
            )
        assert response.status_code == 400
        assert "Login failed for username=nobody" in caplog.text
        assert secret not in caplog.text

    def test_login_rejects_bad_csrf(self, client: TestClient):
        client.get("/auth/login")
        response = client.post(
            "/auth/login",
            data={
                "username": os.environ["DEMO_USERNAME"],
                "password": os.environ["DEMO_PASSWORD"],
                "csrf_token": "not-the-real-token",
            },
            follow_redirects=False,
        )
        assert response.status_code == 403

    def test_get_logout_removed(self, client: TestClient):
        assert client.get("/auth/logout").status_code == 405


class TestHealthSqlite:
    def test_health_includes_sqlite(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert "sqlite_ping" in body
        assert body["sqlite_ping"] == "ok"


class TestRoot:
    def test_root_redirects_to_ui(self, client: TestClient):
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/ui/dashboard"
