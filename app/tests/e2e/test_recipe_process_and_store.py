"""
E2E tests for full recipe processing pipeline with DB insertion and deletion.
"""

from app.tests.utils.constants import HTTP_OK, HTTP_NOT_FOUND
from app.tests.clients.api_client import APIClient


def test_process_and_store_then_delete(api_client: APIClient) -> None:
    input_text = (
        "Simple Tomato Pasta\n\n"
        "Servings: 2\n"
        "Total time: 20 minutes\n\n"
        "Ingredients:\n- 200g pasta\n- 1 cup tomato sauce\n- 1 tbsp olive oil\n\n"
        "Instructions:\n1. Boil pasta\n2. Warm sauce with olive oil\n3. Combine and serve\n"
    )

    create_response = api_client.recipes.process_and_store_recipe(input_text)
    assert create_response["status_code"] == HTTP_OK, (
        f"Expected 200 but got {create_response['status_code']}"
    )

    create_data = create_response["data"]
    assert create_data.get("success") is True
    recipe_id = create_data.get("recipe_id")
    assert recipe_id

    get_response = api_client.recipes.get_recipe(recipe_id)
    assert get_response["status_code"] == HTTP_OK
    assert get_response["data"].get("success") is True

    delete_response = api_client.recipes.delete_recipe(recipe_id)
    assert delete_response["status_code"] == HTTP_OK
    assert delete_response["data"] is True

    missing_response = api_client.recipes.get_recipe(recipe_id)
    assert missing_response["status_code"] == HTTP_NOT_FOUND
