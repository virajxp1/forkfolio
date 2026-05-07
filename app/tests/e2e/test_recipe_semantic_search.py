"""E2E coverage for semantic recipe search."""

import uuid

from app.tests.clients.api_client import APIClient
from app.tests.utils.constants import HTTP_OK
from app.tests.utils.helpers import maybe_throttle


def test_semantic_search_finds_newly_stored_recipe(api_client: APIClient) -> None:
    run_id = uuid.uuid4().hex[:8]
    input_text = (
        f"Semantic Citrus Pasta {run_id}\n\n"
        "Servings: 2\n"
        "Total time: 20 minutes\n\n"
        "Ingredients:\n- 200g pasta\n- 1 tbsp olive oil\n- 1 tsp lemon zest\n"
        "- 1 tbsp lemon juice\n- 1 clove garlic\n"
        f"- 1 tsp test-spice-{run_id}\n\n"
        "Instructions:\n1. Boil pasta.\n"
        "2. Warm oil and garlic.\n"
        "3. Toss with lemon juice, zest, and pasta.\n"
    )

    recipe_id = None
    try:
        maybe_throttle()
        create_response = api_client.recipes.process_and_store_recipe(
            input_text,
            enforce_deduplication=False,
        )
        assert create_response["status_code"] == HTTP_OK
        create_data = create_response["data"]
        assert create_data.get("success") is True
        assert create_data.get("created") is True
        recipe_id = create_data.get("recipe_id")
        assert recipe_id

        stored_title = str(create_data.get("recipe", {}).get("title", "")).strip()
        assert stored_title

        # Quote-wrapped query also validates endpoint-side query normalization.
        maybe_throttle()
        search_response = api_client.recipes.search_semantic(
            query=f'"{stored_title}"',
            limit=10,
        )
        assert search_response["status_code"] == HTTP_OK
        search_data = search_response["data"]
        assert search_data.get("success") is True
        assert search_data.get("query") == stored_title
        results = search_data.get("results")
        assert isinstance(results, list)

        result_ids = [result.get("id") for result in results]
        assert recipe_id in result_ids, (
            f"Expected recipe {recipe_id} in semantic results for '{stored_title}', "
            f"got ids={result_ids}"
        )
    finally:
        if recipe_id:
            api_client.recipes.delete_recipe(recipe_id)
