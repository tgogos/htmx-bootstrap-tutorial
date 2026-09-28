"""Tutorial landing page and lessons 1–6."""

from fastapi.testclient import TestClient

from tests.conftest import session_csrf_headers

API_BOOKS = "/api/books"


def _create_book(
    auth_client: TestClient,
    title: str = "Lesson Book",
    *,
    category: str = "other",
) -> str:
    headers = session_csrf_headers(auth_client)
    created = auth_client.post(
        f"{API_BOOKS}/",
        json={"title": title, "author": "Tutor", "year": 1991, "category": category},
        headers=headers,
    )
    assert created.status_code == 201
    return created.json()["id"]


class TestTutorial:
    def test_lessons_require_login(self, client: TestClient):
        for path in (
            "/ui/tutorial",
            "/ui/tutorial/1",
            "/ui/tutorial/2",
            "/ui/tutorial/3",
            "/ui/tutorial/4",
            "/ui/tutorial/5",
            "/ui/tutorial/6",
        ):
            response = client.get(path, follow_redirects=False)
            assert response.status_code == 303
            assert response.headers["location"] == "/auth/login"

    def test_home_lists_first_lessons(self, auth_client: TestClient):
        page = auth_client.get("/ui/tutorial")
        assert page.status_code == 200
        assert "HTMX 4.0.0" in page.text
        assert 'href="/ui/tutorial/1"' in page.text
        assert 'href="/ui/tutorial/2"' in page.text
        assert 'href="/ui/tutorial/3"' in page.text
        assert 'href="/ui/tutorial/4"' in page.text
        assert 'href="/ui/tutorial/5"' in page.text
        assert 'href="/ui/tutorial/6"' in page.text
        assert "books table" in page.text.lower()

    def test_lesson_1_is_an_ordinary_link(self, auth_client: TestClient):
        book_id = _create_book(auth_client)
        page = auth_client.get("/ui/tutorial/1")
        assert page.status_code == 200
        assert f'href="/ui/tutorial/books/{book_id}"' in page.text
        assert "hx-get" not in page.text

        book = auth_client.get(f"/ui/tutorial/books/{book_id}")
        assert book.status_code == 200
        assert "Lesson Book" in book.text
        assert "<html" in book.text.lower()

    def test_lesson_2_fragment(self, auth_client: TestClient):
        book_id = _create_book(auth_client, "Fragment Book")
        page = auth_client.get("/ui/tutorial/2")
        assert page.status_code == 200
        assert f'hx-get="/ui/tutorial/books/{book_id}/card"' in page.text
        assert 'hx-target="#book-slot"' in page.text
        assert 'hx-swap="innerHTML"' in page.text

        card = auth_client.get(f"/ui/tutorial/books/{book_id}/card")
        assert card.status_code == 200
        assert "Fragment Book" in card.text
        assert "<html" not in card.text.lower()
        assert "Artificial wait" not in card.text

    def test_lesson_3_names_the_wait(self, auth_client: TestClient):
        book_id = _create_book(auth_client, "Slow Book")
        page = auth_client.get("/ui/tutorial/3")
        assert page.status_code == 200
        assert f'hx-get="/ui/tutorial/books/{book_id}/card?delay=1.5"' in page.text
        assert 'hx-indicator="#lesson-indicator"' in page.text
        assert "books list does not sleep" in page.text

        card = auth_client.get(
            f"/ui/tutorial/books/{book_id}/card",
            params={"delay": 0},
        )
        assert card.status_code == 200
        assert "Slow Book" in card.text
        assert "Artificial wait" not in card.text

    def test_lesson_4_offers_two_swaps(self, auth_client: TestClient):
        book_id = _create_book(auth_client, "Swap Book")
        page = auth_client.get("/ui/tutorial/4")
        assert page.status_code == 200
        assert page.text.count(f'hx-get="/ui/tutorial/books/{book_id}/card"') == 2
        assert 'hx-swap="innerHTML"' in page.text
        assert 'hx-swap="beforeend"' in page.text
        assert 'hx-target="#book-shelf"' in page.text

    def test_lesson_5_category_list(self, auth_client: TestClient):
        _create_book(auth_client, "AAA Tutorial Fiction", category="fiction")
        page = auth_client.get("/ui/tutorial/5")
        assert page.status_code == 200
        assert 'hx-get="/ui/tutorial/books"' in page.text
        assert 'hx-trigger="change"' in page.text
        assert 'name="category"' in page.text

        listing = auth_client.get("/ui/tutorial/books", params={"category": "fiction"})
        assert listing.status_code == 200
        assert "AAA Tutorial Fiction" in listing.text
        assert "<html" not in listing.text.lower()
        assert "Artificial wait" not in listing.text

    def test_lesson_6_debounce_and_stale_search(self, auth_client: TestClient):
        _create_book(auth_client, "ZZZ Tutorial Searchable")
        page = auth_client.get("/ui/tutorial/6")
        assert page.status_code == 200
        assert page.text.count('hx-trigger="keyup changed delay:300ms, search"') == 3
        assert 'id="fresh-q"' in page.text
        assert 'hx-sync="this:replace"' in page.text
        assert "books list does not sleep" in page.text

        fresh = auth_client.get(
            "/ui/tutorial/books",
            params={"q": "ZZZ Tutorial", "slow": 1},
        )
        assert fresh.status_code == 200
        assert "ZZZ Tutorial Searchable" in fresh.text
        assert "Artificial wait" not in fresh.text

        slow = auth_client.get("/ui/tutorial/books", params={"q": "Z", "slow": 1})
        assert slow.status_code == 200
        assert "Artificial wait" in slow.text
        assert "books list does not do this" in slow.text

    def test_books_history_restore_is_a_full_page(self, auth_client: TestClient):
        partial = auth_client.get("/ui/books", headers={"HX-Request": "true"})
        assert partial.status_code == 200
        assert "<html" not in partial.text.lower()

        restored = auth_client.get(
            "/ui/books",
            headers={
                "HX-Request": "true",
                "HX-History-Restore-Request": "true",
            },
        )
        assert restored.status_code == 200
        assert "<html" in restored.text.lower()
        assert "htmx.min.js" in restored.text
