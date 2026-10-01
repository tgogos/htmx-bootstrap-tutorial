"""Tutorial landing page and lessons 1–15."""

import re

from fastapi.testclient import TestClient

from tests.conftest import session_csrf_headers

API_BOOKS = "/api/books"


def _create_book(
    auth_client: TestClient,
    title: str = "Lesson Book",
    *,
    author: str = "Tutor",
    category: str = "other",
) -> str:
    headers = session_csrf_headers(auth_client)
    created = auth_client.post(
        f"{API_BOOKS}/",
        json={"title": title, "author": author, "year": 1991, "category": category},
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
            "/ui/tutorial/7",
            "/ui/tutorial/8",
            "/ui/tutorial/9",
            "/ui/tutorial/10",
            "/ui/tutorial/11",
            "/ui/tutorial/12",
            "/ui/tutorial/12/books",
            "/ui/tutorial/13",
            "/ui/tutorial/13/clock",
            "/ui/tutorial/14",
            "/ui/tutorial/15",
            "/ui/tutorial/15/room",
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
        assert 'href="/ui/tutorial/7"' in page.text
        assert 'href="/ui/tutorial/8"' in page.text
        assert 'href="/ui/tutorial/9"' in page.text
        assert 'href="/ui/tutorial/10"' in page.text
        assert 'href="/ui/tutorial/11"' in page.text
        assert 'href="/ui/tutorial/12"' in page.text
        assert 'href="/ui/tutorial/13"' in page.text
        assert 'href="/ui/tutorial/14"' in page.text
        assert 'href="/ui/tutorial/15"' in page.text
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

    def test_lesson_7_returns_html_for_a_bad_form(self, auth_client: TestClient):
        page = auth_client.get("/ui/tutorial/7")
        assert page.status_code == 200
        assert 'hx-post="/ui/tutorial/books"' in page.text
        assert 'hx-target="#add-result"' in page.text
        assert 'name="csrf_token"' in page.text

        headers = session_csrf_headers(auth_client)
        rejected = auth_client.post(
            "/ui/tutorial/books",
            data={"title": "", "author": "Tutor", "year": ""},
            headers=headers,
        )
        assert rejected.status_code == 400
        assert "Title and author are required." in rejected.text
        assert "<html" not in rejected.text.lower()

        saved = auth_client.post(
            "/ui/tutorial/books",
            data={"title": "Tutorial Added", "author": "Tutor", "year": "nope"},
            headers=headers,
        )
        assert saved.status_code == 400
        assert "Year must be a number." in saved.text

        ok = auth_client.post(
            "/ui/tutorial/books",
            data={"title": "Tutorial Added", "author": "Tutor", "year": "1991"},
            headers=headers,
        )
        assert ok.status_code == 200
        assert "Tutorial Added" in ok.text
        assert "Saved." in ok.text
        assert "<html" not in ok.text.lower()

    def test_lesson_8_edits_and_deletes_the_practice_book(self, auth_client: TestClient):
        page = auth_client.get("/ui/tutorial/8")
        assert page.status_code == 200
        assert 'hx-trigger="confirmed-delete"' in page.text
        match = re.search(r'hx-delete="/ui/tutorial/books/([^"]+)"', page.text)
        assert match is not None
        book_id = match.group(1)

        headers = session_csrf_headers(auth_client)
        rejected = auth_client.put(
            f"/ui/tutorial/books/{book_id}",
            data={"title": "", "author": "Tutor"},
            headers=headers,
        )
        assert rejected.status_code == 400
        assert "Title and author are required." in rejected.text

        updated = auth_client.put(
            f"/ui/tutorial/books/{book_id}",
            data={"title": "Practice renamed", "author": "Tutor"},
            headers=headers,
        )
        assert updated.status_code == 200
        assert "Practice renamed" in updated.text
        assert 'hx-trigger="confirmed-delete"' in updated.text

        deleted = auth_client.delete(
            f"/ui/tutorial/books/{book_id}",
            headers=headers,
        )
        assert deleted.status_code == 200
        assert "Deleted." in deleted.text
        assert "<html" not in deleted.text.lower()

    def test_lesson_9_triggers_a_toast(self, auth_client: TestClient):
        page = auth_client.get("/ui/tutorial/9")
        assert page.status_code == 200
        assert 'hx-swap="none"' in page.text
        match = re.search(r'hx-post="/ui/tutorial/books/([^"]+)/announce"', page.text)
        assert match is not None

        announced = auth_client.post(
            f"/ui/tutorial/books/{match.group(1)}/announce",
            headers=session_csrf_headers(auth_client),
        )
        assert announced.status_code == 200
        assert announced.text == ""
        assert "showToast" in announced.headers["hx-trigger"]
        assert "not in the HTML" in announced.headers["hx-trigger"]

    def test_lesson_10_pushes_a_url_and_restores_a_full_page(self, auth_client: TestClient):
        for number in range(1, 7):
            _create_book(
                auth_client,
                title=f"Shelf {number:02d}",
                author=f"Author {7 - number:02d}",
            )
        page = auth_client.get("/ui/tutorial/10")
        assert page.status_code == 200
        assert "<html" in page.text.lower()
        assert 'hx-push-url="true"' in page.text
        assert "Shelf 01" in page.text
        assert "Shelf 06" not in page.text

        nxt = auth_client.get(
            "/ui/tutorial/10",
            params={"page": 2, "ordering": "title"},
            headers={"HX-Request": "true"},
        )
        assert nxt.status_code == 200
        assert "<html" not in nxt.text.lower()
        assert "Shelf 06" in nxt.text
        assert "Shelf 01" not in nxt.text

        by_author = auth_client.get(
            "/ui/tutorial/10",
            params={"ordering": "author"},
            headers={"HX-Request": "true"},
        )
        assert by_author.status_code == 200
        assert by_author.text.index("Shelf 06") < by_author.text.index("Shelf 02")
        assert "Shelf 01" not in by_author.text

        restored = auth_client.get(
            "/ui/tutorial/10",
            params={"page": 2, "ordering": "title"},
            headers={
                "HX-Request": "true",
                "HX-History-Restore-Request": "true",
            },
        )
        assert restored.status_code == 200
        assert "<html" in restored.text.lower()
        assert "Shelf 06" in restored.text
        assert "Put the page in the address bar" in restored.text

    def test_lesson_11_points_at_the_books_table(self, auth_client: TestClient):
        page = auth_client.get("/ui/tutorial/11")
        assert page.status_code == 200
        assert 'hx-get="/ui/books"' in page.text
        assert 'hx-target="#books-panel"' in page.text
        assert 'id="books-panel"' in page.text
        assert 'href="/ui/books"' in page.text
        assert "HX-History-Restore-Request" in page.text

    def test_lesson_12_loads_titles_when_revealed(self, auth_client: TestClient):
        _create_book(auth_client, "000 Lazy Title", author="Lazy Author")
        page = auth_client.get("/ui/tutorial/12")
        assert page.status_code == 200
        assert 'hx-get="/ui/tutorial/12/books"' in page.text
        assert 'hx-trigger="revealed"' in page.text
        assert 'id="lazy-books"' in page.text
        assert "000 Lazy Title" not in page.text

        fragment = auth_client.get("/ui/tutorial/12/books")
        assert fragment.status_code == 200
        assert "<html" not in fragment.text.lower()
        assert "000 Lazy Title" in fragment.text
        assert "Lazy Author" in fragment.text
        assert "Artificial wait" in fragment.text
        assert "held for 1 second" in fragment.text

    def test_lesson_13_polls_the_server_clock(self, auth_client: TestClient):
        page = auth_client.get("/ui/tutorial/13")
        assert page.status_code == 200
        assert 'hx-get="/ui/tutorial/13/clock"' in page.text
        assert 'hx-trigger="every 2s"' in page.text
        assert 'id="server-clock"' in page.text
        assert "The time appears here, then updates every two seconds." in page.text
        assert "<time" not in page.text

        fragment = auth_client.get("/ui/tutorial/13/clock")
        assert fragment.status_code == 200
        assert "<html" not in fragment.text.lower()
        assert "Server time:" in fragment.text
        assert "UTC" in fragment.text
        assert re.search(r"\d{2}:\d{2}:\d{2} UTC", fragment.text)

    def test_lesson_14_form_hears_search_and_menu(self, auth_client: TestClient):
        _create_book(auth_client, "Heard Fiction Title", category="fiction")
        _create_book(auth_client, "Heard History Title", category="biography")
        page = auth_client.get("/ui/tutorial/14")
        assert page.status_code == 200
        assert page.text.count('hx-get="/ui/tutorial/books"') == 2
        assert 'hx-target="#catalog-results"' in page.text
        assert "from:select[name='category']" in page.text
        assert "from:input[name='q']" in page.text
        assert 'name="q"' in page.text
        assert 'name="category"' in page.text
        assert 'id="catalog-results"' in page.text
        assert "Heard Fiction Title" not in page.text

        both = auth_client.get(
            "/ui/tutorial/books",
            params={"q": "Heard", "category": "fiction"},
        )
        assert both.status_code == 200
        assert "<html" not in both.text.lower()
        assert "Heard Fiction Title" in both.text
        assert "Heard History Title" not in both.text
        assert "in Fiction" in both.text

    def test_lesson_15_boosts_the_main_region(self, auth_client: TestClient):
        page = auth_client.get("/ui/tutorial/15")
        assert page.status_code == 200
        assert 'href="/ui/tutorial/15/room"' in page.text
        assert 'hx-boost="true"' in page.text
        assert 'hx-target="#main"' in page.text
        assert 'hx-select="#main"' in page.text
        assert 'hx-swap="outerHTML"' in page.text

        room = auth_client.get(
            "/ui/tutorial/15/room",
            headers={"HX-Request": "true", "HX-Boosted": "true"},
        )
        assert room.status_code == 200
        assert "<html" in room.text.lower()
        assert 'id="main"' in room.text
        assert "The other room" in room.text
        assert "admin-sidebar" in room.text

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
