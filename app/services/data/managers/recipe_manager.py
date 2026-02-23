import uuid
from typing import Optional

from app.api.schemas import Recipe
from app.core.exceptions import DatabaseError

from .base import BaseManager

RECIPE_WITH_CHILDREN_SQL = """
SELECT r.*,
    COALESCE(i.ingredients, ARRAY[]::text[]) AS ingredients,
    COALESCE(s.instructions, ARRAY[]::text[]) AS instructions
FROM recipes r
LEFT JOIN LATERAL (
    SELECT array_agg(ingredient_text ORDER BY order_index) AS ingredients
    FROM recipe_ingredients
    WHERE recipe_id = r.id
) i ON true
LEFT JOIN LATERAL (
    SELECT array_agg(instruction_text ORDER BY step_number) AS instructions
    FROM recipe_instructions
    WHERE recipe_id = r.id
) s ON true
WHERE r.id = %s
"""
EMBEDDINGS_SELECT_SQL = """
SELECT id, embedding_type, embedding, created_at
FROM recipe_embeddings
WHERE recipe_id = %s
ORDER BY created_at
"""
SIMILAR_RECIPES_BY_EMBEDDING_SQL = """
SELECT
    r.id AS recipe_id,
    r.title AS recipe_name,
    e.embedding <=> %s::vector AS distance
FROM recipe_embeddings e
JOIN recipes r ON r.id = e.recipe_id
WHERE e.embedding_type = %s
  AND e.embedding <=> %s::vector <= %s
ORDER BY distance
LIMIT %s
"""


class RecipeManager(BaseManager):
    @staticmethod
    def _generate_id() -> str:
        return str(uuid.uuid4())

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

    def _fetch_recipe_with_children(self, cursor, recipe_id: str) -> Optional[dict]:
        cursor.execute(RECIPE_WITH_CHILDREN_SQL, (recipe_id,))
        row = cursor.fetchone()
        if not row:
            return None
        recipe_data = dict(row)
        recipe_data["ingredients"] = list(recipe_data.get("ingredients") or [])
        recipe_data["instructions"] = list(recipe_data.get("instructions") or [])
        return recipe_data

    def _fetch_embeddings(self, cursor, recipe_id: str) -> list[dict]:
        cursor.execute(EMBEDDINGS_SELECT_SQL, (recipe_id,))
        embeddings = [dict(row) for row in cursor.fetchall()]
        for row in embeddings:
            row["embedding"] = self._normalize_embedding_value(row.get("embedding"))
        return embeddings

    @staticmethod
    def _format_semantic_search_row(row: dict) -> dict:
        distance_value = row.get("distance")
        distance = float(distance_value) if distance_value is not None else None
        return {
            "id": row.get("recipe_id"),
            "name": row.get("recipe_name"),
            "distance": distance,
        }

    def delete_recipe(self, recipe_id: str) -> bool:
        """Delete a recipe by ID"""
        try:
            with self.get_db_context() as (_conn, cursor):
                sql = "DELETE FROM recipes WHERE id = %s"
                cursor.execute(sql, (recipe_id,))
                return cursor.rowcount > 0
        except Exception as e:
            raise DatabaseError(f"Failed to delete recipe: {e!s}") from e

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
                recipe_data = self._fetch_recipe_with_children(cursor, recipe_id)
                if not recipe_data:
                    return None
                return recipe_data

        except Exception as e:
            raise DatabaseError(f"Failed to get recipe: {e!s}") from e

    def get_full_recipe_with_embeddings(self, recipe_id: str) -> Optional[dict]:
        """Get a complete recipe with ingredients, instructions, and embeddings."""
        try:
            with self.get_db_context() as (_conn, cursor):
                recipe_data = self._fetch_recipe_with_children(cursor, recipe_id)
                if not recipe_data:
                    return None

                recipe_data["embeddings"] = self._fetch_embeddings(cursor, recipe_id)
                return recipe_data

        except Exception as e:
            raise DatabaseError(f"Failed to get recipe with embeddings: {e!s}") from e

    def search_recipes_by_embedding(
        self,
        embedding: list[float],
        embedding_type: str,
        limit: int = 10,
        max_distance: float = 0.35,
    ) -> list[dict]:
        """Find recipes with embeddings closest to the provided embedding."""
        try:
            with self.get_db_context() as (_conn, cursor):
                cursor.execute(
                    SIMILAR_RECIPES_BY_EMBEDDING_SQL,
                    (
                        embedding,
                        embedding_type,
                        embedding,
                        max_distance,
                        limit,
                    ),
                )
                rows = cursor.fetchall()
                return [self._format_semantic_search_row(dict(row)) for row in rows]
        except Exception as e:
            raise DatabaseError(f"Failed to search recipes by embedding: {e!s}") from e

    def find_nearest_embedding(
        self,
        embedding: list[float],
        embedding_type: str,
    ) -> Optional[dict]:
        """Find the nearest embedding by cosine distance."""
        try:
            with self.get_db_context() as (_conn, cursor):
                sql = """
                SELECT recipe_id, embedding_type, embedding <=> %s::vector AS distance
                FROM recipe_embeddings
                WHERE embedding_type = %s
                ORDER BY distance
                LIMIT 1
                """
                cursor.execute(sql, (embedding, embedding_type))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            raise DatabaseError(f"Failed to find nearest embedding: {e!s}") from e
