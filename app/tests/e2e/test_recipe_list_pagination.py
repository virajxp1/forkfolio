"""E2E coverage for cursor pagination on recipe listing."""

import uuid

from app.tests.clients.api_client import APIClient
from app.tests.utils.constants import HTTP_OK
from app.tests.utils.helpers import maybe_throttle


def test_list_recipes_paginates_with_unique_ids(api_client: APIClient) -> None:
    run_id = uuid.uuid4().hex[:8]
    created_recipe_ids: list[str] = []
    paged_recipe_ids: list[str] = []
    cursor: str | None = None

    try:
        for index in range(5):
            maybe_throttle()
            create_response = api_client.recipes.process_and_store_recipe(
                (
                    f"Pagination Test Recipe {index} {run_id}\n\n"
                    "Servings: 2\n"
                    "Total time: 20 minutes\n\n"
                    "Ingredients:\n- 200g pasta\n- 1 tbsp olive oil\n"
                    f"- 1 tsp pagination-marker-{run_id}-{index}\n\n"
                    "Instructions:\n1. Boil pasta.\n2. Toss and serve.\n"
                ),
                enforce_deduplication=False,
            )
            assert create_response["status_code"] == HTTP_OK
            create_data = create_response["data"]
            assert create_data.get("success") is True
            assert create_data.get("created") is True
            recipe_id = create_data.get("recipe_id")
            assert isinstance(recipe_id, str)
            created_recipe_ids.append(recipe_id)

        for page_index in range(5):
            maybe_throttle()
            list_response = api_client.recipes.list_recipes(limit=1, cursor=cursor)
            assert list_response["status_code"] == HTTP_OK
            list_data = list_response["data"]
            assert list_data.get("success") is True

            recipes = list_data.get("recipes")
            assert isinstance(recipes, list)
            assert len(recipes) == 1

            recipe_id = recipes[0].get("id")
            assert isinstance(recipe_id, str)
            paged_recipe_ids.append(recipe_id)

            cursor = list_data.get("next_cursor")
            if page_index < 4:
                assert isinstance(cursor, str)
                assert cursor

        assert len(paged_recipe_ids) == 5
        assert len(set(paged_recipe_ids)) == 5
    finally:
        for recipe_id in created_recipe_ids:
            api_client.recipes.delete_recipe(recipe_id)
