from contextlib import contextmanager

from app.services.data.managers.recipe_book_manager import RecipeBookManager


class FakeCursor:
    def __init__(
        self,
        *,
        fetchone_results=None,
        fetchall_results=None,
        rowcount_sequence=None,
    ):
        self._fetchone_results = list(fetchone_results or [])
        self._fetchall_results = list(fetchall_results or [])
        self._rowcount_sequence = list(rowcount_sequence or [])
        self.rowcount = 0
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))
        if self._rowcount_sequence:
            self.rowcount = self._rowcount_sequence.pop(0)

    def fetchone(self):
        if not self._fetchone_results:
            return None
        return self._fetchone_results.pop(0)

    def fetchall(self):
        if not self._fetchall_results:
            return []
        return self._fetchall_results.pop(0)


def _patch_db_context(monkeypatch, manager, cursor):
    def fake_get_db_context():
        @contextmanager
        def _ctx():
            yield None, cursor

        return _ctx()

    monkeypatch.setattr(manager, "get_db_context", fake_get_db_context)


def test_create_recipe_book_inserts_normalized_name(monkeypatch) -> None:
    manager = RecipeBookManager()
    cursor = FakeCursor(
        fetchone_results=[
            {
                "id": "book-1",
                "name": "Italian Recipes",
                "normalized_name": "italian recipes",
                "description": "Classic dishes",
            }
        ]
    )
    _patch_db_context(monkeypatch, manager, cursor)

    recipe_book, created = manager.create_recipe_book(
        name="  Italian   Recipes  ",
        description="Classic dishes",
    )

    assert created is True
    assert recipe_book["id"] == "book-1"
    assert recipe_book["recipe_count"] == 0

    _, params = cursor.executed[0]
    assert params[1] == "Italian Recipes"
    assert params[2] == "italian recipes"


def test_create_recipe_book_returns_existing_on_conflict(monkeypatch) -> None:
    manager = RecipeBookManager()
    cursor = FakeCursor(
        fetchone_results=[
            None,
            {
                "id": "book-existing",
                "name": "Italian Recipes",
                "normalized_name": "italian recipes",
                "description": None,
                "recipe_count": 3,
            },
        ]
    )
    _patch_db_context(monkeypatch, manager, cursor)

    recipe_book, created = manager.create_recipe_book(name="Italian Recipes")

    assert created is False
    assert recipe_book["id"] == "book-existing"
    assert recipe_book["recipe_count"] == 3


def test_add_recipe_to_book_returns_missing_book(monkeypatch) -> None:
    manager = RecipeBookManager()
    cursor = FakeCursor(fetchone_results=[None])
    _patch_db_context(monkeypatch, manager, cursor)

    result = manager.add_recipe_to_book("book-1", "recipe-1")

    assert result == {"book_exists": False, "recipe_exists": True, "added": False}


def test_add_recipe_to_book_returns_missing_recipe(monkeypatch) -> None:
    manager = RecipeBookManager()
    cursor = FakeCursor(fetchone_results=[{"exists": 1}, None])
    _patch_db_context(monkeypatch, manager, cursor)

    result = manager.add_recipe_to_book("book-1", "recipe-1")

    assert result == {"book_exists": True, "recipe_exists": False, "added": False}


def test_add_recipe_to_book_returns_added_flag(monkeypatch) -> None:
    manager = RecipeBookManager()
    cursor = FakeCursor(
        fetchone_results=[{"exists": 1}, {"exists": 1}],
        rowcount_sequence=[0, 0, 1],
    )
    _patch_db_context(monkeypatch, manager, cursor)

    result = manager.add_recipe_to_book("book-1", "recipe-1")

    assert result == {"book_exists": True, "recipe_exists": True, "added": True}


def test_remove_recipe_from_book_returns_removed_flag(monkeypatch) -> None:
    manager = RecipeBookManager()
    cursor = FakeCursor(
        fetchone_results=[{"exists": 1}],
        rowcount_sequence=[0, 1],
    )
    _patch_db_context(monkeypatch, manager, cursor)

    result = manager.remove_recipe_from_book("book-1", "recipe-1")

    assert result == {"book_exists": True, "removed": True}


def test_get_recipe_book_stats_computes_average(monkeypatch) -> None:
    manager = RecipeBookManager()
    cursor = FakeCursor(
        fetchone_results=[
            {
                "total_recipe_books": 2,
                "total_recipe_book_links": 5,
                "unique_recipes_in_books": 4,
            }
        ]
    )
    _patch_db_context(monkeypatch, manager, cursor)

    stats = manager.get_recipe_book_stats()

    assert stats["total_recipe_books"] == 2
    assert stats["total_recipe_book_links"] == 5
    assert stats["unique_recipes_in_books"] == 4
    assert stats["avg_recipes_per_book"] == 2.5


def test_get_recipe_book_stats_handles_zero_books(monkeypatch) -> None:
    manager = RecipeBookManager()
    cursor = FakeCursor(
        fetchone_results=[
            {
                "total_recipe_books": 0,
                "total_recipe_book_links": 0,
                "unique_recipes_in_books": 0,
            }
        ]
    )
    _patch_db_context(monkeypatch, manager, cursor)

    stats = manager.get_recipe_book_stats()

    assert stats["avg_recipes_per_book"] == 0.0
