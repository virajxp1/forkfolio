import uuid
from typing import Optional

from app.api.schemas import Recipe
from app.core.exceptions import DatabaseError

from .base import BaseManager

RECIPE_SELECT_SQL = "SELECT * FROM recipes WHERE id = %s"
INGREDIENTS_SELECT_SQL = """
SELECT ingredient_text
FROM recipe_ingredients
WHERE recipe_id = %s
ORDER BY order_index
"""
INSTRUCTIONS_SELECT_SQL = """
SELECT instruction_text
FROM recipe_instructions
WHERE recipe_id = %s
ORDER BY step_number
"""
EMBEDDINGS_SELECT_SQL = """
SELECT id, embedding_type, embedding, created_at
FROM recipe_embeddings
WHERE recipe_id = %s
ORDER BY created_at
"""


class RecipeManager(BaseManager):
    @staticmethod
    def _generate_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def _to_dict(row) -> Optional[dict]:
        return dict(row) if row else None

    @staticmethod
    def _normalize_embedding_value(embedding_value):
        if embedding_value is None:
            return None
        if hasattr(embedding_value, "tolist"):
            return embedding_value.tolist()
        try:
            return list(embedding_value)
        except TypeError:
            return embedding_value

    @staticmethod
    def _build_update_payload(**kwargs) -> tuple[list[str], list[object]]:
        set_clauses = []
        values = []
        for field, value in kwargs.items():
            if field in ["title", "servings", "total_time"]:
                set_clauses.append(f"{field} = %s")
                values.append(value)
        return set_clauses, values

    def _insert_recipe(
        self,
        cursor,
        recipe_id: str,
        title: str,
        servings: Optional[str],
        total_time: Optional[str],
        is_test_data: bool = False,
        source_url: Optional[str] = None,
    ) -> None:
        if source_url is None:
            sql = """
            INSERT INTO recipes (id, title, servings, total_time, is_test_data)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (recipe_id, title, servings, total_time, is_test_data))
            return

        sql = """
        INSERT INTO recipes (
            id, title, servings, total_time, source_url, is_test_data
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(
            sql,
            (recipe_id, title, servings, total_time, source_url, is_test_data),
        )

    def _insert_ingredients(
        self, cursor, recipe_id: str, ingredients: list[str]
    ) -> None:
        sql = """
        INSERT INTO recipe_ingredients (
            id, recipe_id, ingredient_text, order_index
        )
        VALUES (%s, %s, %s, %s)
        """
        for index, ingredient_text in enumerate(ingredients):
            ingredient_id = self._generate_id()
            cursor.execute(
                sql,
                (ingredient_id, recipe_id, ingredient_text, index),
            )

    def _insert_instructions(
        self, cursor, recipe_id: str, instructions: list[str]
    ) -> None:
        sql = """
        INSERT INTO recipe_instructions (
            id, recipe_id, instruction_text, step_number
        )
        VALUES (%s, %s, %s, %s)
        """
        for step_num, instruction_text in enumerate(instructions, 1):
            instruction_id = self._generate_id()
            cursor.execute(
                sql,
                (instruction_id, recipe_id, instruction_text, step_num),
            )

    def _insert_embedding(
        self,
        cursor,
        recipe_id: str,
        embedding_type: str,
        embedding: list[float],
    ) -> None:
        sql = """
        INSERT INTO recipe_embeddings (id, recipe_id, embedding_type, embedding)
        VALUES (%s, %s, %s, %s)
        """
        embedding_id = self._generate_id()
        cursor.execute(sql, (embedding_id, recipe_id, embedding_type, embedding))

    def _fetch_recipe(self, cursor, recipe_id: str) -> Optional[dict]:
        cursor.execute(RECIPE_SELECT_SQL, (recipe_id,))
        return self._to_dict(cursor.fetchone())

    def _fetch_ingredients(self, cursor, recipe_id: str) -> list[str]:
        cursor.execute(INGREDIENTS_SELECT_SQL, (recipe_id,))
        return [row["ingredient_text"] for row in cursor.fetchall()]

    def _fetch_instructions(self, cursor, recipe_id: str) -> list[str]:
        cursor.execute(INSTRUCTIONS_SELECT_SQL, (recipe_id,))
        return [row["instruction_text"] for row in cursor.fetchall()]

    def _fetch_embeddings(self, cursor, recipe_id: str) -> list[dict]:
        cursor.execute(EMBEDDINGS_SELECT_SQL, (recipe_id,))
        embeddings = [dict(row) for row in cursor.fetchall()]
        for row in embeddings:
            row["embedding"] = self._normalize_embedding_value(row.get("embedding"))
        return embeddings

    def create_recipe(
        self,
        title: str,
        servings: Optional[str] = None,
        total_time: Optional[str] = None,
        is_test_data: bool = False,
    ) -> str:
        """Create a new recipe and return its ID"""
        recipe_id = self._generate_id()

        try:
            with self.get_db_context() as (_conn, cursor):
                self._insert_recipe(
                    cursor=cursor,
                    recipe_id=recipe_id,
                    title=title,
                    servings=servings,
                    total_time=total_time,
                    is_test_data=is_test_data,
                )
                return recipe_id
        except Exception as e:
            raise DatabaseError(f"Failed to create recipe: {e!s}") from e

    def get_recipe_by_id(self, recipe_id: str) -> Optional[dict]:
        """Get a recipe by its ID"""
        try:
            with self.get_db_context() as (_conn, cursor):
                return self._fetch_recipe(cursor, recipe_id)
        except Exception as e:
            raise DatabaseError(f"Failed to get recipe by ID: {e!s}") from e

    def get_all_recipes(self, limit: int = 50) -> list[dict]:
        """Get all recipes with optional limit"""
        try:
            with self.get_db_context() as (_conn, cursor):
                sql = "SELECT * FROM recipes ORDER BY created_at DESC LIMIT %s"
                cursor.execute(sql, (limit,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            raise DatabaseError(f"Failed to get all recipes: {e!s}") from e

    def update_recipe(self, recipe_id: str, **kwargs) -> bool:
        """Update recipe fields"""
        if not kwargs:
            return False

        try:
            with self.get_db_context() as (_conn, cursor):
                set_clauses, values = self._build_update_payload(**kwargs)

                if not set_clauses:
                    return False

                sql = (
                    f"UPDATE recipes SET {', '.join(set_clauses)}, "
                    f"updated_at = NOW() WHERE id = %s"
                )
                values.append(recipe_id)

                cursor.execute(sql, values)
                return cursor.rowcount > 0
        except Exception as e:
            raise DatabaseError(f"Failed to update recipe: {e!s}") from e

    def delete_recipe(self, recipe_id: str) -> bool:
        """Delete a recipe by ID"""
        try:
            with self.get_db_context() as (_conn, cursor):
                sql = "DELETE FROM recipes WHERE id = %s"
                cursor.execute(sql, (recipe_id,))
                return cursor.rowcount > 0
        except Exception as e:
            raise DatabaseError(f"Failed to delete recipe: {e!s}") from e

    def search_recipes_by_title(self, search_term: str) -> list[dict]:
        """Simple text search by title"""
        try:
            with self.get_db_context() as (_conn, cursor):
                sql = (
                    "SELECT * FROM recipes WHERE title ILIKE %s "
                    "ORDER BY created_at DESC"
                )
                cursor.execute(sql, (f"%{search_term}%",))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            raise DatabaseError(f"Failed to search recipes: {e!s}") from e

    def create_recipe_from_model(
        self,
        recipe: Recipe,
        source_url: Optional[str] = None,
        embedding_type: Optional[str] = None,
        embedding: Optional[list[float]] = None,
        is_test_data: bool = False,
    ) -> str:
        """Create recipe from a model with ingredients, instructions, and embeddings."""
        recipe_id = self._generate_id()

        try:
            with self.get_db_context() as (_conn, cursor):
                self._insert_recipe(
                    cursor=cursor,
                    recipe_id=recipe_id,
                    title=recipe.title,
                    servings=recipe.servings,
                    total_time=recipe.total_time,
                    source_url=source_url,
                    is_test_data=is_test_data,
                )
                self._insert_ingredients(cursor, recipe_id, recipe.ingredients)
                self._insert_instructions(cursor, recipe_id, recipe.instructions)

                if embedding_type and embedding is not None:
                    self._insert_embedding(
                        cursor=cursor,
                        recipe_id=recipe_id,
                        embedding_type=embedding_type,
                        embedding=embedding,
                    )

                return recipe_id

        except Exception as e:
            raise DatabaseError(f"Failed to create recipe: {e!s}") from e

    def get_full_recipe(self, recipe_id: str) -> Optional[dict]:
        """Get a complete recipe with ingredients and instructions"""
        try:
            with self.get_db_context() as (_conn, cursor):
                recipe_data = self._fetch_recipe(cursor, recipe_id)
                if not recipe_data:
                    return None

                recipe_data["ingredients"] = self._fetch_ingredients(cursor, recipe_id)
                recipe_data["instructions"] = self._fetch_instructions(
                    cursor, recipe_id
                )

                return recipe_data

        except Exception as e:
            raise DatabaseError(f"Failed to get recipe: {e!s}") from e

    def get_full_recipe_with_embeddings(self, recipe_id: str) -> Optional[dict]:
        """Get a complete recipe with ingredients, instructions, and embeddings."""
        try:
            with self.get_db_context() as (_conn, cursor):
                recipe_data = self._fetch_recipe(cursor, recipe_id)
                if not recipe_data:
                    return None

                recipe_data["ingredients"] = self._fetch_ingredients(cursor, recipe_id)
                recipe_data["instructions"] = self._fetch_instructions(
                    cursor, recipe_id
                )
                recipe_data["embeddings"] = self._fetch_embeddings(cursor, recipe_id)

                return recipe_data

        except Exception as e:
            raise DatabaseError(f"Failed to get recipe with embeddings: {e!s}") from e

    def create_recipe_embedding(
        self,
        recipe_id: str,
        embedding_type: str,
        embedding: list[float],
    ) -> None:
        """Store an embedding for a recipe."""
        try:
            with self.get_db_context() as (_conn, cursor):
                self._insert_embedding(
                    cursor=cursor,
                    recipe_id=recipe_id,
                    embedding_type=embedding_type,
                    embedding=embedding,
                )
        except Exception as e:
            raise DatabaseError(f"Failed to create recipe embedding: {e!s}") from e
