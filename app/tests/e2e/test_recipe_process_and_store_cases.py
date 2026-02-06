"""
E2E tests for process-and-store using JSON test cases.
"""

import json
import os

import pytest
from pydantic import ValidationError

from app.api.schemas import Recipe
from app.tests.clients.api_client import APIClient
from app.tests.utils.constants import (
    HTTP_OK,
    HTTP_NOT_FOUND,
    HTTP_UNPROCESSABLE_ENTITY,
)
from app.tests.utils.helpers import truncate_debug_text


def load_test_cases():
    """Load test cases from JSON file."""
    test_cases_file = os.path.join(os.path.dirname(__file__), "test_cases.json")
    with open(test_cases_file) as f:
        return json.load(f)


@pytest.mark.parametrize(
    "test_case", [pytest.param(case, id=case["name"]) for case in load_test_cases()]
)
def test_process_and_store_from_json(api_client: APIClient, test_case: dict) -> None:
    """Test process-and-store for all cases defined in test_cases.json."""
    input_text = test_case["input_text"]
    expect_error = test_case.get("expect_error", False)

    response = api_client.recipes.process_and_store_recipe(input_text)

    # Debug Output (always show for failed tests)
    print(f"\n=== Test: {test_case['name']} ===")
    print(f"Input: {truncate_debug_text(input_text)}")
    print(f"Status: {response['status_code']}")
    print(f"Response: {response.get('data', response.get('text', 'No data'))}")

    if expect_error:
        if response["status_code"] == HTTP_UNPROCESSABLE_ENTITY:
            return
        if response["status_code"] == HTTP_OK and "error" in response["data"]:
            return
        raise AssertionError(f"Expected error but got status {response['status_code']}")

    assert response["status_code"] == HTTP_OK, (
        f"Expected 200 but got {response['status_code']}"
    )

    response_data = response["data"]
    assert "error" not in response_data, (
        f"Expected success but got error: {response_data.get('error')}"
    )
    assert response_data.get("success") is True

    recipe_data = response_data.get("recipe")
    assert recipe_data, "Expected recipe data in response"

    try:
        Recipe.model_validate(recipe_data)
    except ValidationError as e:
        raise AssertionError(
            f"Response recipe doesn't match Recipe model: {e}\nResponse: {recipe_data}"
        ) from e


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

    get_all_response = api_client.recipes.get_recipe_all(recipe_id)
    assert get_all_response["status_code"] == HTTP_OK
    all_data = get_all_response["data"]
    assert all_data.get("success") is True
    recipe_all = all_data.get("recipe")
    assert recipe_all
    assert recipe_all.get("id") == recipe_id
    assert isinstance(recipe_all.get("ingredients"), list)
    assert isinstance(recipe_all.get("instructions"), list)
    assert isinstance(recipe_all.get("embeddings"), list)

    delete_response = api_client.recipes.delete_recipe(recipe_id)
    assert delete_response["status_code"] == HTTP_OK
    assert delete_response["data"] is True

    missing_response = api_client.recipes.get_recipe(recipe_id)
    assert missing_response["status_code"] == HTTP_NOT_FOUND
