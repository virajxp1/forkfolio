import uuid
from typing import Optional

from app.schemas.recipe import Recipe

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

        sql = """
        INSERT INTO recipes (id, title, servings, total_time)
        VALUES (%s, %s, %s, %s)
        """

        self.cursor.execute(sql, (recipe_id, title, servings, total_time))
        self.db.commit()
        return recipe_id

    def get_recipe_by_id(self, recipe_id: str) -> Optional[dict]:
        """Get a recipe by its ID"""
        sql = "SELECT * FROM recipes WHERE id = %s"

        self.cursor.execute(sql, (recipe_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_all_recipes(self, limit: int = 50) -> list[dict]:
        """Get all recipes with optional limit"""
        sql = "SELECT * FROM recipes ORDER BY created_at DESC LIMIT %s"

        self.cursor.execute(sql, (limit,))
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def update_recipe(self, recipe_id: str, **kwargs) -> bool:
        """Update recipe fields"""
        if not kwargs:
            return False

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

        self.cursor.execute(sql, values)
        self.db.commit()
        return self.cursor.rowcount > 0

    def delete_recipe(self, recipe_id: str) -> bool:
        """Delete a recipe by ID"""
        sql = "DELETE FROM recipes WHERE id = %s"

        self.cursor.execute(sql, (recipe_id,))
        self.db.commit()
        return self.cursor.rowcount > 0

    def search_recipes_by_title(self, search_term: str) -> list[dict]:
        """Simple text search by title"""
        sql = "SELECT * FROM recipes WHERE title ILIKE %s ORDER BY created_at DESC"

        self.cursor.execute(sql, (f"%{search_term}%",))
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def create_recipe_from_model(
        self, recipe: Recipe, source_url: Optional[str] = None
    ) -> str:
        """Create recipe from Recipe model with ingredients and instructions"""
        recipe_id = str(uuid.uuid4())

        try:
            # Insert main recipe
            recipe_sql = """
            INSERT INTO recipes (id, title, servings, total_time, source_url)
            VALUES (%s, %s, %s, %s, %s)
            """

            self.cursor.execute(
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
                self.cursor.execute(
                    ingredient_sql, (ingredient_id, recipe_id, ingredient_text, index)
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
                self.cursor.execute(
                    instruction_sql,
                    (instruction_id, recipe_id, instruction_text, step_num),
                )

            self.db.commit()
            return recipe_id

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to create recipe: {e!s}") from e

    def get_full_recipe(self, recipe_id: str) -> Optional[dict]:
        """Get a complete recipe with ingredients and instructions"""
        try:
            # Get basic recipe info
            recipe_sql = "SELECT * FROM recipes WHERE id = %s"
            self.cursor.execute(recipe_sql, (recipe_id,))
            recipe = self.cursor.fetchone()

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
            self.cursor.execute(ingredients_sql, (recipe_id,))
            ingredients = [row["ingredient_text"] for row in self.cursor.fetchall()]

            # Get instructions
            instructions_sql = """
            SELECT instruction_text 
            FROM recipe_instructions 
            WHERE recipe_id = %s 
            ORDER BY step_number
            """
            self.cursor.execute(instructions_sql, (recipe_id,))
            instructions = [row["instruction_text"] for row in self.cursor.fetchall()]

            recipe_data["ingredients"] = ingredients
            recipe_data["instructions"] = instructions

            return recipe_data

        except Exception as e:
            raise Exception(f"Failed to get recipe: {e!s}") from e
