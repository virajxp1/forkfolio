"""
E2E tests for recipe extraction endpoint.
"""

import json
import os

import pytest
from pydantic import ValidationError

from app.api.schemas import Recipe
from app.tests.utils.constants import (
    HTTP_OK,
    HTTP_UNPROCESSABLE_ENTITY,
)
from app.tests.utils.helpers import truncate_debug_text
from app.tests.utils.assertions import assert_recipe_has_content
from app.tests.clients.api_client import APIClient


def load_test_cases():
    """Load test cases from JSON file."""
    test_cases_file = os.path.join(os.path.dirname(__file__), "test_cases.json")
    with open(test_cases_file) as f:
        return json.load(f)


class TestRecipeExtraction:
    """Test suite for recipe extraction functionality."""

    @pytest.mark.parametrize(
        "test_case", [pytest.param(case, id=case["name"]) for case in load_test_cases()]
    )
    def test_recipe_extraction_from_json(
        self, api_client: APIClient, test_case: dict
    ) -> None:
        """Test recipe extraction for all cases defined in test_cases.json."""
        # Input
        input_text = test_case["input_text"]
        expect_error = test_case.get("expect_error", False)
        allow_empty_result = test_case.get("allow_empty_result", False)

        # API Call - use the recipe utilities client for recipe extraction
        response = api_client.recipe_utilities.extract_recipe(input_text)

        # Debug Output (always show for failed tests)
        print(f"\n=== Test: {test_case['name']} ===")
        print(f"Input: {truncate_debug_text(input_text)}")
        print(f"Status: {response['status_code']}")
        print(f"Response: {response.get('data', response.get('text', 'No data'))}")

        # Assertions
        if expect_error:
            # Expecting an error response
            if response["status_code"] == HTTP_UNPROCESSABLE_ENTITY:
                return  # 422 validation error is expected
            elif response["status_code"] == HTTP_OK and "error" in response["data"]:
                return  # 200 with error field is expected
            else:
                raise AssertionError(
                    f"Expected error but got status {response['status_code']}"
                )

        # Expecting success response
        assert response["status_code"] == HTTP_OK, (
            f"Expected 200 but got {response['status_code']}"
        )

        response_data = response["data"]
        assert "error" not in response_data, (
            f"Expected success but got error: {response_data.get('error')}"
        )

        # Validate response matches Recipe Pydantic model exactly
        try:
            recipe = Recipe.model_validate(response_data)
            print(f"✓ Valid Recipe model: {recipe}")
        except ValidationError as e:
            raise AssertionError(
                f"Response doesn't match Recipe model: {e}\nResponse: {response_data}"
            ) from e

        # Check for content using utility function
        assert_recipe_has_content(response_data, allow_empty=allow_empty_result)

    def test_server_health(self, api_client: APIClient) -> None:
        """Test that the server is running and healthy."""
        response = api_client.health.get_root()
        assert response["status_code"] == HTTP_OK
