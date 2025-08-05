"""
E2E tests for recipe extraction endpoint.
"""

import json
import logging
import os
from typing import Any

import pytest
import requests
from pydantic import ValidationError

from app.schemas.recipe import Recipe

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
HTTP_OK = 200
HTTP_UNPROCESSABLE_ENTITY = 422
REQUEST_TIMEOUT = 30
DEBUG_TEXT_LENGTH = 100


def load_test_cases():
    """Load test cases from JSON file."""
    test_cases_file = os.path.join(os.path.dirname(__file__), "test_cases.json")
    with open(test_cases_file) as f:
        return json.load(f)


@pytest.fixture
def api_client(server: str):
    """Provide an API client for each test."""
    return APIClient(server)


class APIClient:
    """Helper class for making API requests."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.endpoint = f"{base_url}/api/v1/ingest-raw-recipe"

    def extract_recipe(self, input_text: str) -> dict[str, Any]:
        """Make a request to the recipe extraction API."""
        payload = {"raw_input": input_text}

        response = requests.post(
            self.endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )

        # Don't raise for status - let tests handle different status codes
        return {
            "status_code": response.status_code,
            "data": (
                response.json()
                if response.headers.get("content-type", "").startswith(
                    "application/json"
                )
                else None
            ),
            "text": response.text,
        }


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

        # API Call
        response = api_client.extract_recipe(input_text)

        # Debug Output (always show for failed tests)
        print(f"\n=== Test: {test_case['name']} ===")
        truncated_input = input_text[:DEBUG_TEXT_LENGTH]
        if len(input_text) > DEBUG_TEXT_LENGTH:
            truncated_input += "..."
        print(f"Input: {truncated_input}")
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
        assert (
            response["status_code"] == HTTP_OK
        ), f"Expected 200 but got {response['status_code']}"

        response_data = response["data"]
        assert (
            "error" not in response_data
        ), f"Expected success but got error: {response_data.get('error')}"

        # Validate response matches Recipe Pydantic model exactly
        try:
            recipe = Recipe.model_validate(response_data)
            print(f"✓ Valid Recipe model: {recipe}")
        except ValidationError as e:
            raise AssertionError(
                f"Response doesn't match Recipe model: {e}\nResponse: {response_data}"
            ) from e

        # Check for content if not allowing empty results
        if not allow_empty_result:
            has_content = (
                response_data["title"].strip() or len(response_data["ingredients"]) > 0
            )
            assert has_content, (
                f"Recipe should have title or ingredients but got: "
                f"title='{response_data['title']}', "
                f"ingredients={response_data['ingredients']}"
            )

    def test_server_health(self, server: str) -> None:
        """Test that the server is running and healthy."""
        response = requests.get(f"{server}/api/v1/", timeout=5)
        assert response.status_code == HTTP_OK
