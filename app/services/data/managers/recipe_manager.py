import uuid
from typing import Optional

from app.core.exceptions import DatabaseError
from app.api.schemas import Recipe

from .base import BaseManager


class RecipeManager(BaseManager):
    def create_recipe(
        self,
        title: str,
        servings: Optional[str] = None,
        total_time: Optional[str] = None,
    ) -> str:
        """Create a new recipe and return its ID"""
        recipe_id = str(uuid.uuid4())

        try:
            with self.get_db_context() as (conn, cursor):
                sql = """
                INSERT INTO recipes (id, title, servings, total_time)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (recipe_id, title, servings, total_time))
                return recipe_id
        except Exception as e:
            raise DatabaseError(f"Failed to create recipe: {e!s}") from e

    def get_recipe_by_id(self, recipe_id: str) -> Optional[dict]:
        """Get a recipe by its ID"""
        try:
            with self.get_db_context() as (conn, cursor):
                sql = "SELECT * FROM recipes WHERE id = %s"
                cursor.execute(sql, (recipe_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            raise DatabaseError(f"Failed to get recipe by ID: {e!s}") from e

    def get_all_recipes(self, limit: int = 50) -> list[dict]:
        """Get all recipes with optional limit"""
        try:
            with self.get_db_context() as (conn, cursor):
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
            with self.get_db_context() as (conn, cursor):
                # Build dynamic UPDATE query
                set_clauses = []
                values = []

                for field, value in kwargs.items():
                    if field in ["title", "servings", "total_time"]:
                        set_clauses.append(f"{field} = %s")
                        values.append(value)

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
            with self.get_db_context() as (conn, cursor):
                sql = "DELETE FROM recipes WHERE id = %s"
                cursor.execute(sql, (recipe_id,))
                return cursor.rowcount > 0
        except Exception as e:
            raise DatabaseError(f"Failed to delete recipe: {e!s}") from e

    def search_recipes_by_title(self, search_term: str) -> list[dict]:
        """Simple text search by title"""
        try:
            with self.get_db_context() as (conn, cursor):
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
        self, recipe: Recipe, source_url: Optional[str] = None
    ) -> str:
        """Create recipe from Recipe model with ingredients and instructions"""
        recipe_id = str(uuid.uuid4())

        try:
            with self.get_db_context() as (conn, cursor):
                # Insert main recipe
                recipe_sql = """
                INSERT INTO recipes (id, title, servings, total_time, source_url)
                VALUES (%s, %s, %s, %s, %s)
                """

                cursor.execute(
                    recipe_sql,
                    (
                        recipe_id,
                        recipe.title,
                        recipe.servings,
                        recipe.total_time,
                        source_url,
                    ),
                )

                # Insert ingredients
                for index, ingredient_text in enumerate(recipe.ingredients):
                    ingredient_sql = """
                    INSERT INTO recipe_ingredients (
                        id, recipe_id, ingredient_text, order_index
                    )
                    VALUES (%s, %s, %s, %s)
                    """
                    ingredient_id = str(uuid.uuid4())
                    cursor.execute(
                        ingredient_sql,
                        (ingredient_id, recipe_id, ingredient_text, index),
                    )

                # Insert instructions
                for step_num, instruction_text in enumerate(recipe.instructions, 1):
                    instruction_sql = """
                    INSERT INTO recipe_instructions (
                        id, recipe_id, instruction_text, step_number
                    )
                    VALUES (%s, %s, %s, %s)
                    """
                    instruction_id = str(uuid.uuid4())
                    cursor.execute(
                        instruction_sql,
                        (instruction_id, recipe_id, instruction_text, step_num),
                    )

                # Transaction will auto-commit via context manager
                return recipe_id

        except Exception as e:
            raise DatabaseError(f"Failed to create recipe: {e!s}") from e

    def get_full_recipe(self, recipe_id: str) -> Optional[dict]:
        """Get a complete recipe with ingredients and instructions"""
        try:
            with self.get_db_context() as (conn, cursor):
                # Get basic recipe info
                recipe_sql = "SELECT * FROM recipes WHERE id = %s"
                cursor.execute(recipe_sql, (recipe_id,))
                recipe = cursor.fetchone()

                if not recipe:
                    return None

                recipe_data = dict(recipe)

                # Get ingredients
                ingredients_sql = """
                SELECT ingredient_text 
                FROM recipe_ingredients 
                WHERE recipe_id = %s 
                ORDER BY order_index
                """
                cursor.execute(ingredients_sql, (recipe_id,))
                ingredients = [row["ingredient_text"] for row in cursor.fetchall()]

                # Get instructions
                instructions_sql = """
                SELECT instruction_text 
                FROM recipe_instructions 
                WHERE recipe_id = %s 
                ORDER BY step_number
                """
                cursor.execute(instructions_sql, (recipe_id,))
                instructions = [row["instruction_text"] for row in cursor.fetchall()]

                recipe_data["ingredients"] = ingredients
                recipe_data["instructions"] = instructions

                return recipe_data

        except Exception as e:
            raise DatabaseError(f"Failed to get recipe: {e!s}") from e

    def get_full_recipe_with_embeddings(self, recipe_id: str) -> Optional[dict]:
        """Get a complete recipe with ingredients, instructions, and embeddings."""
        try:
            with self.get_db_context() as (conn, cursor):
                recipe_sql = "SELECT * FROM recipes WHERE id = %s"
                cursor.execute(recipe_sql, (recipe_id,))
                recipe = cursor.fetchone()

                if not recipe:
                    return None

                recipe_data = dict(recipe)

                ingredients_sql = """
                SELECT ingredient_text 
                FROM recipe_ingredients 
                WHERE recipe_id = %s 
                ORDER BY order_index
                """
                cursor.execute(ingredients_sql, (recipe_id,))
                ingredients = [row["ingredient_text"] for row in cursor.fetchall()]

                instructions_sql = """
                SELECT instruction_text 
                FROM recipe_instructions 
                WHERE recipe_id = %s 
                ORDER BY step_number
                """
                cursor.execute(instructions_sql, (recipe_id,))
                instructions = [row["instruction_text"] for row in cursor.fetchall()]

                embeddings_sql = """
                SELECT id, embedding_type, embedding, created_at
                FROM recipe_embeddings
                WHERE recipe_id = %s
                ORDER BY created_at
                """
                cursor.execute(embeddings_sql, (recipe_id,))
                embeddings = [dict(row) for row in cursor.fetchall()]
                for embedding in embeddings:
                    embedding_vector = embedding.get("embedding")
                    if embedding_vector is None:
                        continue
                    if hasattr(embedding_vector, "tolist"):
                        embedding["embedding"] = embedding_vector.tolist()
                    else:
                        try:
                            embedding["embedding"] = list(embedding_vector)
                        except TypeError:
                            embedding["embedding"] = embedding_vector

                recipe_data["ingredients"] = ingredients
                recipe_data["instructions"] = instructions
                recipe_data["embeddings"] = embeddings

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
            with self.get_db_context() as (conn, cursor):
                sql = """
                INSERT INTO recipe_embeddings (id, recipe_id, embedding_type, embedding)
                VALUES (%s, %s, %s, %s)
                """
                embedding_id = str(uuid.uuid4())
                cursor.execute(
                    sql,
                    (embedding_id, recipe_id, embedding_type, embedding),
                )
        except Exception as e:
            raise DatabaseError(f"Failed to create recipe embedding: {e!s}") from e

    def find_nearest_embedding(
        self,
        embedding: list[float],
        embedding_type: str,
    ) -> Optional[dict]:
        """Find the nearest embedding by cosine distance."""
        try:
            with self.get_db_context() as (conn, cursor):
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
