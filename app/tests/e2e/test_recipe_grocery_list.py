"""E2E coverage for grocery list creation from selected recipe IDs."""

import uuid

from app.api.schemas import Recipe
from app.services.data.managers.recipe_manager import RecipeManager
from app.tests.clients.api_client import APIClient
from app.tests.utils.constants import HTTP_OK
from app.tests.utils.helpers import maybe_throttle


def test_create_grocery_list_from_two_recipes(api_client: APIClient) -> None:
    run_id = uuid.uuid4().hex[:8]
    recipe_manager = RecipeManager()
    recipe_one_id = recipe_manager.create_recipe_from_model(
        Recipe(
            title=f"Groceries Pasta {run_id}",
            servings="2",
            total_time="20 minutes",
            ingredients=[
                "200g pasta",
                "2 tomatoes",
                "2 cloves garlic",
                f"1 tsp spice-{run_id}",
            ],
            instructions=[
                "Boil pasta.",
                "Cook tomatoes and garlic.",
                "Mix everything.",
            ],
        ),
        is_test_data=True,
    )
    recipe_two_id = recipe_manager.create_recipe_from_model(
        Recipe(
            title=f"Groceries Curry {run_id}",
            servings="3",
            total_time="30 minutes",
            ingredients=[
                "1 can chickpeas",
                "1 onion",
                "1 tsp cumin",
                f"1 tsp herb-{run_id}",
            ],
            instructions=[
                "Saute onion.",
                "Add chickpeas and cumin.",
                "Simmer and serve.",
            ],
        ),
        is_test_data=True,
    )
    try:
        maybe_throttle()
        grocery_response = api_client.recipes.create_grocery_list(
            [recipe_one_id, recipe_two_id]
        )
        assert grocery_response["status_code"] == HTTP_OK
        grocery_data = grocery_response["data"]
        assert grocery_data.get("success") is True
        assert grocery_data.get("recipe_ids") == [recipe_one_id, recipe_two_id]
        ingredients = grocery_data.get("ingredients")
        assert isinstance(ingredients, list)
        assert ingredients
        assert grocery_data.get("count") == len(ingredients)

        normalized = [str(item).lower() for item in ingredients]

        # Validate that the grocery list preserves signals from both source recipes
        # without requiring one exact LLM phrasing.
        recipe_one_markers = ("tomato", "garlic")
        recipe_two_markers = ("chickpea", "garbanzo", "onion", "cumin")

        assert any(
            marker in item for item in normalized for marker in recipe_one_markers
        )
        assert any(
            marker in item for item in normalized for marker in recipe_two_markers
        )
    finally:
        if recipe_one_id:
            recipe_manager.delete_recipe(recipe_one_id)
        if recipe_two_id:
            recipe_manager.delete_recipe(recipe_two_id)
