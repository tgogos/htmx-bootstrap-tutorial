"""Demo data seeding.

Startup (`seed_demo_user` in lifespan) only creates the admin when `users` is empty.

Richer sample users + books are opt-in via:

    python -m app.seed
    make seed
"""

from __future__ import annotations

import asyncio

from app.auth.passwords import hash_password
from app.auth.seed import seed_demo_user
from app.auth.users import create_user, get_user_by_username
from app.core import config
from app.db import books as books_repo
from app.db.books import BOOK_CATEGORIES
from app.db.connection import close_sqlite, connect_to_sqlite, get_connection

# Shared password for sample non-admin accounts (documented in README).
SAMPLE_PASSWORD = "demo123"

SAMPLE_USERS: list[tuple[str, str, str]] = [
    ("viewer", SAMPLE_PASSWORD, "viewer"),
    ("editor", SAMPLE_PASSWORD, "editor"),
]

# About 100 well-known titles so page size and column sorting are obvious.
SAMPLE_BOOKS: list[dict[str, object]] = [
    {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "year": 1813,
        "notes": "Classic novel of manners.",
    },
    {
        "title": "The Hobbit",
        "author": "J. R. R. Tolkien",
        "year": 1937,
        "notes": "There and back again.",
    },
    {
        "title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "notes": "Desert planet politics and spice.",
    },
    {
        "title": "Neuromancer",
        "author": "William Gibson",
        "year": 1984,
        "notes": "Cyberpunk cornerstone.",
    },
    {
        "title": "The Left Hand of Darkness",
        "author": "Ursula K. Le Guin",
        "year": 1969,
        "notes": "Ambassador on a winter world.",
    },
    {
        "title": "Kindred",
        "author": "Octavia E. Butler",
        "year": 1979,
        "notes": "Time travel and American history.",
    },
    {
        "title": "The Name of the Rose",
        "author": "Umberto Eco",
        "year": 1980,
        "notes": "Monastery mystery.",
    },
    {
        "title": "Invisible Cities",
        "author": "Italo Calvino",
        "year": 1972,
        "notes": "Marco Polo describes cities to Kublai Khan.",
    },
    {
        "title": "Frankenstein",
        "author": "Mary Shelley",
        "year": 1818,
        "notes": "Creature and creator.",
    },
    {
        "title": "Dracula",
        "author": "Bram Stoker",
        "year": 1897,
        "notes": "Epistolary vampire novel.",
    },
    {
        "title": "Moby-Dick",
        "author": "Herman Melville",
        "year": 1851,
        "notes": "Obsession at sea.",
    },
    {
        "title": "Jane Eyre",
        "author": "Charlotte Brontë",
        "year": 1847,
        "notes": "Gothic bildungsroman.",
    },
    {
        "title": "Wuthering Heights",
        "author": "Emily Brontë",
        "year": 1847,
        "notes": "Stormy moorland passions.",
    },
    {
        "title": "1984",
        "author": "George Orwell",
        "year": 1949,
        "notes": "Surveillance and Newspeak.",
    },
    {
        "title": "Brave New World",
        "author": "Aldous Huxley",
        "year": 1932,
        "notes": "Engineered happiness.",
    },
    {
        "title": "Fahrenheit 451",
        "author": "Ray Bradbury",
        "year": 1953,
        "notes": "Firemen who burn books.",
    },
    {
        "title": "The Handmaid's Tale",
        "author": "Margaret Atwood",
        "year": 1985,
        "notes": "Gilead and resistance.",
    },
    {
        "title": "Beloved",
        "author": "Toni Morrison",
        "year": 1987,
        "notes": "Memory and haunting.",
    },
    {
        "title": "One Hundred Years of Solitude",
        "author": "Gabriel García Márquez",
        "year": 1967,
        "notes": "Macondo across generations.",
    },
    {
        "title": "The Stranger",
        "author": "Albert Camus",
        "year": 1942,
        "notes": "Absurdity in Algiers.",
    },
    {
        "title": "Crime and Punishment",
        "author": "Fyodor Dostoevsky",
        "year": 1866,
        "notes": "Guilt after a crime.",
    },
    {
        "title": "The Trial",
        "author": "Franz Kafka",
        "year": 1925,
        "notes": "Arrested without knowing why.",
    },
    {
        "title": "To Kill a Mockingbird",
        "author": "Harper Lee",
        "year": 1960,
        "notes": "Justice in Maycomb.",
    },
    {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "notes": "Jazz Age longing.",
    },
    {
        "title": "Mrs Dalloway",
        "author": "Virginia Woolf",
        "year": 1925,
        "notes": "One day in London.",
    },
    {
        "title": "Things Fall Apart",
        "author": "Chinua Achebe",
        "year": 1958,
        "notes": "Igbo life and colonial rupture.",
    },
    {
        "title": "The Dispossessed",
        "author": "Ursula K. Le Guin",
        "year": 1974,
        "notes": "Anarres and Urras.",
    },
    {
        "title": "Hyperion",
        "author": "Dan Simmons",
        "year": 1989,
        "notes": "Pilgrims to the Time Tombs.",
    },
]

# Extra titles so the catalog is about 100. Category is set explicitly.
MORE_BOOKS: list[dict[str, object]] = [
    {"title": "Don Quixote", "author": "Miguel de Cervantes", "year": 1605, "category": "fiction"},
    {"title": "Hamlet", "author": "William Shakespeare", "year": 1603, "category": "fiction"},
    {"title": "The Divine Comedy", "author": "Dante Alighieri", "year": 1320, "category": "fiction"},
    {"title": "Candide", "author": "Voltaire", "year": 1759, "category": "fiction"},
    {"title": "The Brothers Karamazov", "author": "Fyodor Dostoevsky", "year": 1880, "category": "fiction"},
    {"title": "Anna Karenina", "author": "Leo Tolstoy", "year": 1878, "category": "fiction"},
    {"title": "War and Peace", "author": "Leo Tolstoy", "year": 1869, "category": "fiction"},
    {"title": "Madame Bovary", "author": "Gustave Flaubert", "year": 1857, "category": "fiction"},
    {"title": "Les Misérables", "author": "Victor Hugo", "year": 1862, "category": "fiction"},
    {"title": "Great Expectations", "author": "Charles Dickens", "year": 1861, "category": "fiction"},
    {"title": "A Tale of Two Cities", "author": "Charles Dickens", "year": 1859, "category": "fiction"},
    {"title": "The Adventures of Huckleberry Finn", "author": "Mark Twain", "year": 1884, "category": "fiction"},
    {"title": "The Picture of Dorian Gray", "author": "Oscar Wilde", "year": 1890, "category": "fiction"},
    {"title": "Heart of Darkness", "author": "Joseph Conrad", "year": 1899, "category": "fiction"},
    {"title": "The Metamorphosis", "author": "Franz Kafka", "year": 1915, "category": "fiction"},
    {"title": "To the Lighthouse", "author": "Virginia Woolf", "year": 1927, "category": "fiction"},
    {"title": "The Sun Also Rises", "author": "Ernest Hemingway", "year": 1926, "category": "fiction"},
    {"title": "The Old Man and the Sea", "author": "Ernest Hemingway", "year": 1952, "category": "fiction"},
    {"title": "Their Eyes Were Watching God", "author": "Zora Neale Hurston", "year": 1937, "category": "fiction"},
    {"title": "The Grapes of Wrath", "author": "John Steinbeck", "year": 1939, "category": "fiction"},
    {"title": "Of Mice and Men", "author": "John Steinbeck", "year": 1937, "category": "fiction"},
    {"title": "Catch-22", "author": "Joseph Heller", "year": 1961, "category": "fiction"},
    {"title": "Slaughterhouse-Five", "author": "Kurt Vonnegut", "year": 1969, "category": "fiction"},
    {"title": "The Catcher in the Rye", "author": "J. D. Salinger", "year": 1951, "category": "fiction"},
    {"title": "On the Road", "author": "Jack Kerouac", "year": 1957, "category": "fiction"},
    {"title": "Song of Solomon", "author": "Toni Morrison", "year": 1977, "category": "fiction"},
    {"title": "The Color Purple", "author": "Alice Walker", "year": 1982, "category": "fiction"},
    {"title": "White Teeth", "author": "Zadie Smith", "year": 2000, "category": "fiction"},
    {"title": "Never Let Me Go", "author": "Kazuo Ishiguro", "year": 2005, "category": "fiction"},
    {"title": "The Remains of the Day", "author": "Kazuo Ishiguro", "year": 1989, "category": "fiction"},
    {"title": "Midnight's Children", "author": "Salman Rushdie", "year": 1981, "category": "fiction"},
    {"title": "The God of Small Things", "author": "Arundhati Roy", "year": 1997, "category": "fiction"},
    {"title": "Half of a Yellow Sun", "author": "Chimamanda Ngozi Adichie", "year": 2006, "category": "fiction"},
    {"title": "The Kite Runner", "author": "Khaled Hosseini", "year": 2003, "category": "fiction"},
    {"title": "Pachinko", "author": "Min Jin Lee", "year": 2017, "category": "fiction"},
    {"title": "Love in the Time of Cholera", "author": "Gabriel García Márquez", "year": 1985, "category": "fiction"},
    {"title": "Pedro Páramo", "author": "Juan Rulfo", "year": 1955, "category": "fiction"},
    {"title": "The Master and Margarita", "author": "Mikhail Bulgakov", "year": 1967, "category": "fiction"},
    {"title": "Norwegian Wood", "author": "Haruki Murakami", "year": 1987, "category": "fiction"},
    {"title": "Foundation", "author": "Isaac Asimov", "year": 1951, "category": "scifi"},
    {"title": "I, Robot", "author": "Isaac Asimov", "year": 1950, "category": "scifi"},
    {"title": "The Martian Chronicles", "author": "Ray Bradbury", "year": 1950, "category": "scifi"},
    {"title": "Do Androids Dream of Electric Sheep?", "author": "Philip K. Dick", "year": 1968, "category": "scifi"},
    {"title": "The Lathe of Heaven", "author": "Ursula K. Le Guin", "year": 1971, "category": "scifi"},
    {"title": "Snow Crash", "author": "Neal Stephenson", "year": 1992, "category": "scifi"},
    {"title": "Ancillary Justice", "author": "Ann Leckie", "year": 2013, "category": "scifi"},
    {"title": "The Fifth Season", "author": "N. K. Jemisin", "year": 2015, "category": "scifi"},
    {"title": "Station Eleven", "author": "Emily St. John Mandel", "year": 2014, "category": "scifi"},
    {"title": "The Hitchhiker's Guide to the Galaxy", "author": "Douglas Adams", "year": 1979, "category": "scifi"},
    {"title": "Ender's Game", "author": "Orson Scott Card", "year": 1985, "category": "scifi"},
    {"title": "The War of the Worlds", "author": "H. G. Wells", "year": 1898, "category": "scifi"},
    {"title": "A Wizard of Earthsea", "author": "Ursula K. Le Guin", "year": 1968, "category": "fantasy"},
    {"title": "The Lion, the Witch and the Wardrobe", "author": "C. S. Lewis", "year": 1950, "category": "fantasy"},
    {"title": "The Fellowship of the Ring", "author": "J. R. R. Tolkien", "year": 1954, "category": "fantasy"},
    {"title": "American Gods", "author": "Neil Gaiman", "year": 2001, "category": "fantasy"},
    {"title": "The Name of the Wind", "author": "Patrick Rothfuss", "year": 2007, "category": "fantasy"},
    {"title": "Jonathan Strange & Mr Norrell", "author": "Susanna Clarke", "year": 2004, "category": "fantasy"},
    {"title": "Circe", "author": "Madeline Miller", "year": 2018, "category": "fantasy"},
    {"title": "The Murder of Roger Ackroyd", "author": "Agatha Christie", "year": 1926, "category": "mystery"},
    {"title": "Murder on the Orient Express", "author": "Agatha Christie", "year": 1934, "category": "mystery"},
    {"title": "The Maltese Falcon", "author": "Dashiell Hammett", "year": 1930, "category": "mystery"},
    {"title": "The Big Sleep", "author": "Raymond Chandler", "year": 1939, "category": "mystery"},
    {"title": "The Hound of the Baskervilles", "author": "Arthur Conan Doyle", "year": 1902, "category": "mystery"},
    {"title": "In Cold Blood", "author": "Truman Capote", "year": 1966, "category": "nonfiction"},
    {"title": "The Diary of a Young Girl", "author": "Anne Frank", "year": 1947, "category": "nonfiction"},
    {"title": "A Brief History of Time", "author": "Stephen Hawking", "year": 1988, "category": "nonfiction"},
    {"title": "Sapiens", "author": "Yuval Noah Harari", "year": 2011, "category": "nonfiction"},
    {"title": "Silent Spring", "author": "Rachel Carson", "year": 1962, "category": "nonfiction"},
    {"title": "Walden", "author": "Henry David Thoreau", "year": 1854, "category": "nonfiction"},
    {"title": "The Prince", "author": "Niccolò Machiavelli", "year": 1532, "category": "nonfiction"},
    {"title": "A Room of One's Own", "author": "Virginia Woolf", "year": 1929, "category": "nonfiction"},
    {"title": "The Fire Next Time", "author": "James Baldwin", "year": 1963, "category": "nonfiction"},
    {"title": "Long Walk to Freedom", "author": "Nelson Mandela", "year": 1994, "category": "biography"},
    {"title": "The Autobiography of Malcolm X", "author": "Malcolm X", "year": 1965, "category": "biography"},
    {"title": "Educated", "author": "Tara Westover", "year": 2018, "category": "biography"},
    {"title": "Becoming", "author": "Michelle Obama", "year": 2018, "category": "biography"},
    {"title": "The Wright Brothers", "author": "David McCullough", "year": 2015, "category": "biography"},
    {"title": "Meditations", "author": "Marcus Aurelius", "year": 180, "category": "other"},
]

SAMPLE_BOOKS.extend(MORE_BOOKS)

_TITLE_CATEGORY: dict[str, str] = {
    "Pride and Prejudice": "fiction",
    "The Hobbit": "fantasy",
    "Dune": "scifi",
    "Neuromancer": "scifi",
    "The Left Hand of Darkness": "scifi",
    "Kindred": "scifi",
    "The Name of the Rose": "mystery",
    "Invisible Cities": "fiction",
    "Frankenstein": "fiction",
    "Dracula": "fiction",
    "Moby-Dick": "fiction",
    "Jane Eyre": "fiction",
    "Wuthering Heights": "fiction",
    "1984": "fiction",
    "Brave New World": "scifi",
    "Fahrenheit 451": "scifi",
    "The Handmaid's Tale": "fiction",
    "Beloved": "fiction",
    "One Hundred Years of Solitude": "fiction",
    "The Stranger": "fiction",
    "Crime and Punishment": "fiction",
    "The Trial": "fiction",
    "To Kill a Mockingbird": "fiction",
    "The Great Gatsby": "fiction",
    "Mrs Dalloway": "fiction",
    "Things Fall Apart": "fiction",
    "The Dispossessed": "scifi",
    "Hyperion": "scifi",
}

async def seed_sample_users() -> list[str]:
    """Create sample role users if missing. Returns usernames created."""
    created: list[str] = []
    for username, password, role in SAMPLE_USERS:
        if await get_user_by_username(username) is not None:
            continue
        await create_user(username, hash_password(password), role=role)
        created.append(username)
    return created


_CATEGORY_CYCLE = sorted(BOOK_CATEGORIES)


def _sample_meta(index: int, book: dict[str, object]) -> dict[str, object]:
    """Fill category / ISBN / pages / availability for demo variety."""
    title = str(book["title"])
    category = book.get("category") or _TITLE_CATEGORY.get(title)
    if category not in BOOK_CATEGORIES:
        category = _CATEGORY_CYCLE[index % len(_CATEGORY_CYCLE)]
    return {
        **book,
        "category": category,
        "isbn": f"978-{1000000000 + index:010d}",
        "page_count": 180 + (index * 37) % 700,
        "available": index % 5 != 0,
    }


async def _book_id_by_title(title: str) -> str | None:
    conn = get_connection()
    async with conn.execute(
        "SELECT id, isbn FROM books WHERE title = ? LIMIT 1",
        (title,),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return None
    return row["id"]


async def _book_needs_enrichment(book_id: str) -> bool:
    conn = get_connection()
    async with conn.execute(
        "SELECT isbn, added_by_user_id FROM books WHERE id = ?",
        (book_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return False
    return row["isbn"] is None or row["added_by_user_id"] is None


async def seed_sample_books() -> tuple[int, int]:
    """Insert or enrich sample books. Returns (created, enriched)."""
    admin = await get_user_by_username(config.DEMO_USERNAME)
    editor = await get_user_by_username("editor")
    adder_ids = [u["id"] for u in (admin, editor) if u is not None]

    created = 0
    enriched = 0
    for index, raw in enumerate(SAMPLE_BOOKS):
        book = _sample_meta(index, raw)
        title = str(book["title"])
        adder = adder_ids[index % len(adder_ids)] if adder_ids else None
        book_id = await _book_id_by_title(title)

        if book_id is None:
            await books_repo.create_book(
                title=title,
                author=str(book["author"]),
                year=book["year"] if book["year"] is not None else None,  # type: ignore[arg-type]
                notes=str(book["notes"]) if book.get("notes") else None,
                category=str(book["category"]),
                isbn=str(book["isbn"]),
                page_count=int(book["page_count"]),  # type: ignore[arg-type]
                available=bool(book["available"]),
                added_by_user_id=adder,
            )
            created += 1
            continue

        if await _book_needs_enrichment(book_id):
            conn = get_connection()
            await conn.execute(
                """
                UPDATE books
                SET category = ?, isbn = ?, page_count = ?, available = ?,
                    added_by_user_id = COALESCE(added_by_user_id, ?)
                WHERE id = ?
                """,
                (
                    str(book["category"]),
                    str(book["isbn"]),
                    int(book["page_count"]),  # type: ignore[arg-type]
                    1 if book["available"] else 0,
                    adder,
                    book_id,
                ),
            )
            await conn.commit()
            enriched += 1
            continue

        conn = get_connection()
        async with conn.execute(
            "SELECT category FROM books WHERE id = ?",
            (book_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is not None and row["category"] != book["category"]:
            await conn.execute(
                "UPDATE books SET category = ? WHERE id = ?",
                (str(book["category"]), book_id),
            )
            await conn.commit()
            enriched += 1

    return created, enriched


async def run_seed() -> None:
    """Connect, ensure demo admin, add sample users/books (idempotent), disconnect."""
    await connect_to_sqlite()
    try:
        await seed_demo_user()
        created_users = await seed_sample_users()
        books_created, books_enriched = await seed_sample_books()

        if created_users:
            print(
                f"✅ Seeded users: {', '.join(created_users)} "
                f"(password {SAMPLE_PASSWORD!r})"
            )
        else:
            print("ℹ️  Sample users already present (viewer, editor)")

        if books_created or books_enriched:
            print(
                f"✅ Books seed: {books_created} created, {books_enriched} enriched "
                f"({len(SAMPLE_BOOKS)} samples; default UI page size is 10)"
            )
        else:
            print("ℹ️  All sample books already present with metadata")
    finally:
        await close_sqlite()


def main() -> None:
    asyncio.run(run_seed())


if __name__ == "__main__":
    main()
