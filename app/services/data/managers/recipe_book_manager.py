import uuid
from typing import Optional

from app.core.exceptions import DatabaseError

from .base import BaseManager

RECIPE_BOOK_WITH_COUNT_BY_ID_SQL = """
SELECT rb.*,
    COUNT(rbr.recipe_id)::int AS recipe_count
FROM recipe_books rb
LEFT JOIN recipe_book_recipes rbr ON rbr.recipe_book_id = rb.id
WHERE rb.id = %s
GROUP BY rb.id
"""
RECIPE_BOOK_WITH_COUNT_BY_NAME_SQL = """
SELECT rb.*,
    COUNT(rbr.recipe_id)::int AS recipe_count
FROM recipe_books rb
LEFT JOIN recipe_book_recipes rbr ON rbr.recipe_book_id = rb.id
WHERE rb.normalized_name = %s
GROUP BY rb.id
"""
RECIPE_BOOKS_LIST_SQL = """
SELECT rb.*,
    COUNT(rbr.recipe_id)::int AS recipe_count
FROM recipe_books rb
LEFT JOIN recipe_book_recipes rbr ON rbr.recipe_book_id = rb.id
GROUP BY rb.id
ORDER BY rb.created_at DESC
LIMIT %s
"""
RECIPE_IDS_FOR_BOOK_SQL = """
SELECT recipe_id
FROM recipe_book_recipes
WHERE recipe_book_id = %s
ORDER BY added_at ASC
"""
RECIPE_BOOKS_FOR_RECIPE_SQL = """
SELECT rb.*,
    (
        SELECT COUNT(*)::int
        FROM recipe_book_recipes rbr2
        WHERE rbr2.recipe_book_id = rb.id
    ) AS recipe_count
FROM recipe_books rb
JOIN recipe_book_recipes rbr ON rbr.recipe_book_id = rb.id
WHERE rbr.recipe_id = %s
ORDER BY rb.name ASC
"""
INSERT_RECIPE_BOOK_SQL = """
INSERT INTO recipe_books (id, name, normalized_name, description)
VALUES (%s, %s, %s, %s)
ON CONFLICT (normalized_name) DO NOTHING
RETURNING *
"""
INSERT_RECIPE_BOOK_RECIPE_SQL = """
INSERT INTO recipe_book_recipes (recipe_book_id, recipe_id)
VALUES (%s, %s)
ON CONFLICT (recipe_book_id, recipe_id) DO NOTHING
"""
DELETE_RECIPE_BOOK_RECIPE_SQL = """
DELETE FROM recipe_book_recipes
WHERE recipe_book_id = %s AND recipe_id = %s
"""
RECIPE_BOOK_EXISTS_SQL = "SELECT 1 FROM recipe_books WHERE id = %s"
RECIPE_EXISTS_SQL = "SELECT 1 FROM recipes WHERE id = %s"
RECIPE_BOOK_STATS_SQL = """
SELECT
    (SELECT COUNT(*)::int FROM recipe_books) AS total_recipe_books,
    (SELECT COUNT(*)::int FROM recipe_book_recipes) AS total_recipe_book_links,
    (
        SELECT COUNT(DISTINCT recipe_id)::int
        FROM recipe_book_recipes
    ) AS unique_recipes_in_books
"""


class RecipeBookManager(BaseManager):
    @staticmethod
    def _generate_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def _to_dict(row) -> Optional[dict]:
        return dict(row) if row else None

    @staticmethod
    def _normalize_name(name: str) -> str:
        return " ".join(name.strip().split()).lower()

    def _fetch_recipe_book_by_id(self, cursor, recipe_book_id: str) -> Optional[dict]:
        cursor.execute(RECIPE_BOOK_WITH_COUNT_BY_ID_SQL, (recipe_book_id,))
        return self._to_dict(cursor.fetchone())

    def _fetch_recipe_book_by_name(self, cursor, name: str) -> Optional[dict]:
        normalized_name = self._normalize_name(name)
        cursor.execute(RECIPE_BOOK_WITH_COUNT_BY_NAME_SQL, (normalized_name,))
        return self._to_dict(cursor.fetchone())

    @staticmethod
    def _fetch_recipe_ids_for_book(cursor, recipe_book_id: str) -> list[str]:
        cursor.execute(RECIPE_IDS_FOR_BOOK_SQL, (recipe_book_id,))
        rows = cursor.fetchall()
        return [str(row["recipe_id"]) for row in rows]

    @staticmethod
    def _record_exists(cursor, query: str, record_id: str) -> bool:
        cursor.execute(query, (record_id,))
        return cursor.fetchone() is not None

    def create_recipe_book(
        self, name: str, description: Optional[str] = None
    ) -> tuple[dict, bool]:
        normalized_name = self._normalize_name(name)
        clean_name = " ".join(name.strip().split())
        clean_description = description.strip() if description else None
        if clean_description == "":
            clean_description = None
        if not normalized_name:
            raise DatabaseError("Recipe book name cannot be empty")

        try:
            with self.get_db_context() as (_conn, cursor):
                recipe_book_id = self._generate_id()
                cursor.execute(
                    INSERT_RECIPE_BOOK_SQL,
                    (
                        recipe_book_id,
                        clean_name,
                        normalized_name,
                        clean_description,
                    ),
                )
                row = self._to_dict(cursor.fetchone())
                if row:
                    row["recipe_count"] = 0
                    return row, True

                existing = self._fetch_recipe_book_by_name(cursor, clean_name)
                if existing:
                    return existing, False

                raise DatabaseError("Failed to create recipe book")
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to create recipe book: {e!s}") from e

    def get_recipe_book_by_id(self, recipe_book_id: str) -> Optional[dict]:
        try:
            with self.get_db_context() as (_conn, cursor):
                return self._fetch_recipe_book_by_id(cursor, recipe_book_id)
        except Exception as e:
            raise DatabaseError(f"Failed to get recipe book: {e!s}") from e

    def get_recipe_book_by_name(self, name: str) -> Optional[dict]:
        try:
            with self.get_db_context() as (_conn, cursor):
                return self._fetch_recipe_book_by_name(cursor, name)
        except Exception as e:
            raise DatabaseError(f"Failed to get recipe book by name: {e!s}") from e

    def get_full_recipe_book_by_id(self, recipe_book_id: str) -> Optional[dict]:
        try:
            with self.get_db_context() as (_conn, cursor):
                recipe_book = self._fetch_recipe_book_by_id(cursor, recipe_book_id)
                if not recipe_book:
                    return None
                recipe_book["recipe_ids"] = self._fetch_recipe_ids_for_book(
                    cursor, recipe_book_id
                )
                recipe_book["recipe_count"] = len(recipe_book["recipe_ids"])
                return recipe_book
        except Exception as e:
            raise DatabaseError(f"Failed to get full recipe book: {e!s}") from e

    def get_full_recipe_book_by_name(self, name: str) -> Optional[dict]:
        try:
            with self.get_db_context() as (_conn, cursor):
                recipe_book = self._fetch_recipe_book_by_name(cursor, name)
                if not recipe_book:
                    return None
                recipe_book_id = str(recipe_book["id"])
                recipe_book["recipe_ids"] = self._fetch_recipe_ids_for_book(
                    cursor, recipe_book_id
                )
                recipe_book["recipe_count"] = len(recipe_book["recipe_ids"])
                return recipe_book
        except Exception as e:
            raise DatabaseError(f"Failed to get full recipe book by name: {e!s}") from e

    def list_recipe_books(self, limit: int = 50) -> list[dict]:
        try:
            with self.get_db_context() as (_conn, cursor):
                cursor.execute(RECIPE_BOOKS_LIST_SQL, (limit,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            raise DatabaseError(f"Failed to list recipe books: {e!s}") from e

    def recipe_exists(self, recipe_id: str) -> bool:
        try:
            with self.get_db_context() as (_conn, cursor):
                return self._record_exists(cursor, RECIPE_EXISTS_SQL, recipe_id)
        except Exception as e:
            raise DatabaseError(f"Failed to verify recipe existence: {e!s}") from e

    def recipe_book_exists(self, recipe_book_id: str) -> bool:
        try:
            with self.get_db_context() as (_conn, cursor):
                return self._record_exists(
                    cursor, RECIPE_BOOK_EXISTS_SQL, recipe_book_id
                )
        except Exception as e:
            raise DatabaseError(f"Failed to verify recipe book existence: {e!s}") from e

    def add_recipe_to_book(self, recipe_book_id: str, recipe_id: str) -> dict:
        try:
            with self.get_db_context() as (_conn, cursor):
                book_exists = self._record_exists(
                    cursor, RECIPE_BOOK_EXISTS_SQL, recipe_book_id
                )
                if not book_exists:
                    return {"book_exists": False, "recipe_exists": True, "added": False}

                recipe_exists = self._record_exists(
                    cursor, RECIPE_EXISTS_SQL, recipe_id
                )
                if not recipe_exists:
                    return {"book_exists": True, "recipe_exists": False, "added": False}

                cursor.execute(
                    INSERT_RECIPE_BOOK_RECIPE_SQL, (recipe_book_id, recipe_id)
                )
                return {
                    "book_exists": True,
                    "recipe_exists": True,
                    "added": cursor.rowcount > 0,
                }
        except Exception as e:
            raise DatabaseError(f"Failed to add recipe to recipe book: {e!s}") from e

    def remove_recipe_from_book(self, recipe_book_id: str, recipe_id: str) -> dict:
        try:
            with self.get_db_context() as (_conn, cursor):
                book_exists = self._record_exists(
                    cursor, RECIPE_BOOK_EXISTS_SQL, recipe_book_id
                )
                if not book_exists:
                    return {
                        "book_exists": False,
                        "recipe_exists": True,
                        "removed": False,
                    }

                recipe_exists = self._record_exists(
                    cursor, RECIPE_EXISTS_SQL, recipe_id
                )
                if not recipe_exists:
                    return {
                        "book_exists": True,
                        "recipe_exists": False,
                        "removed": False,
                    }

                cursor.execute(
                    DELETE_RECIPE_BOOK_RECIPE_SQL, (recipe_book_id, recipe_id)
                )
                return {
                    "book_exists": True,
                    "recipe_exists": True,
                    "removed": cursor.rowcount > 0,
                }
        except Exception as e:
            raise DatabaseError(
                f"Failed to remove recipe from recipe book: {e!s}"
            ) from e

    def get_recipe_books_for_recipe(self, recipe_id: str) -> list[dict]:
        try:
            with self.get_db_context() as (_conn, cursor):
                cursor.execute(RECIPE_BOOKS_FOR_RECIPE_SQL, (recipe_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            raise DatabaseError(f"Failed to get recipe books for recipe: {e!s}") from e

    def get_recipe_book_stats(self) -> dict:
        try:
            with self.get_db_context() as (_conn, cursor):
                cursor.execute(RECIPE_BOOK_STATS_SQL)
                stats = self._to_dict(cursor.fetchone()) or {
                    "total_recipe_books": 0,
                    "total_recipe_book_links": 0,
                    "unique_recipes_in_books": 0,
                }
                total_books = stats.get("total_recipe_books") or 0
                total_links = stats.get("total_recipe_book_links") or 0
                stats["avg_recipes_per_book"] = (
                    round(total_links / total_books, 2) if total_books else 0.0
                )
                return stats
        except Exception as e:
            raise DatabaseError(f"Failed to get recipe book stats: {e!s}") from e
