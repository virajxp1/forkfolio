"""E2E coverage for grocery list creation from selected recipe IDs."""

import uuid

from app.tests.clients.api_client import APIClient
from app.tests.utils.constants import HTTP_OK
from app.tests.utils.helpers import maybe_throttle


def test_create_grocery_list_from_two_recipes(api_client: APIClient) -> None:
    run_id = uuid.uuid4().hex[:8]
    recipe_one_input = (
        f"Groceries Pasta {run_id}\n\n"
        "Servings: 2\n"
        "Total time: 20 minutes\n\n"
        "Ingredients:\n- 200g pasta\n- 2 tomatoes\n- 2 cloves garlic\n"
        f"- 1 tsp spice-{run_id}\n\n"
        "Instructions:\n1. Boil pasta.\n2. Cook tomatoes and garlic.\n"
        "3. Mix everything.\n"
    )
    recipe_two_input = (
        f"Groceries Curry {run_id}\n\n"
        "Servings: 3\n"
        "Total time: 30 minutes\n\n"
        "Ingredients:\n- 1 can chickpeas\n- 1 onion\n- 1 tsp cumin\n"
        f"- 1 tsp herb-{run_id}\n\n"
        "Instructions:\n1. Saute onion.\n2. Add chickpeas and cumin.\n"
        "3. Simmer and serve.\n"
    )

    recipe_one_id = None
    recipe_two_id = None
    try:
        maybe_throttle()
        create_one_response = api_client.recipes.process_and_store_recipe(
            recipe_one_input,
            enforce_deduplication=False,
        )
        assert create_one_response["status_code"] == HTTP_OK
        create_one_data = create_one_response["data"]
        assert create_one_data.get("success") is True
        assert create_one_data.get("created") is True
        recipe_one_id = create_one_data.get("recipe_id")
        assert recipe_one_id

        maybe_throttle()
        create_two_response = api_client.recipes.process_and_store_recipe(
            recipe_two_input,
            enforce_deduplication=False,
        )
        assert create_two_response["status_code"] == HTTP_OK
        create_two_data = create_two_response["data"]
        assert create_two_data.get("success") is True
        assert create_two_data.get("created") is True
        recipe_two_id = create_two_data.get("recipe_id")
        assert recipe_two_id

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
            api_client.recipes.delete_recipe(recipe_one_id)
        if recipe_two_id:
            api_client.recipes.delete_recipe(recipe_two_id)
