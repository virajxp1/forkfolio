"""
E2E tests for recipe extraction endpoint.
"""

import json
import logging
import os
from typing import Any

import pytest
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
HTTP_OK = 200
HTTP_UNPROCESSABLE_ENTITY = 422
REQUEST_TIMEOUT = 30


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
            "data": response.json()
            if response.headers.get("content-type", "").startswith("application/json")
            else None,
            "text": response.text,
        }


class TestRecipeExtraction:
    """Test suite for recipe extraction functionality."""

    def validate_success_response(self, response_data: dict[str, Any]) -> None:
        """Validate a successful recipe response."""
        required_fields = [
            "title",
            "ingredients",
            "instructions",
            "servings",
            "total_time",
        ]

        # Check for required fields
        for field in required_fields:
            assert field in response_data, f"Missing required field: {field}"

        # Basic type validation
        assert isinstance(response_data["title"], str)
        assert isinstance(response_data["ingredients"], list)
        assert isinstance(response_data["instructions"], list)
        assert isinstance(response_data["servings"], str)
        assert isinstance(response_data["total_time"], str)

    def validate_error_response(self, response_data: dict[str, Any]) -> None:
        """Validate an error response."""
        assert "error" in response_data
        assert response_data.get("success") is False
        assert isinstance(response_data["error"], str)

    @pytest.mark.parametrize(
        "test_case", [pytest.param(case, id=case["name"]) for case in load_test_cases()]
    )
    def test_recipe_extraction_from_json(
        self, api_client: APIClient, test_case: dict
    ) -> None:
        """Test recipe extraction for all cases defined in test_cases.json."""
        expect_error = test_case.get("expect_error", False)
        allow_empty_result = test_case.get("allow_empty_result", False)

        response = api_client.extract_recipe(test_case["input_text"])

        # Log the API response
        logger.info(f"Test case: {test_case['name']}")
        logger.info(f"Status code: {response['status_code']}")
        logger.info(f"Response data: {response.get('data', 'No data')}")
        if response["status_code"] != HTTP_OK:
            logger.info(f"Response text: {response.get('text', 'No text')}")

        # Basic response validation
        assert "status_code" in response
        assert "data" in response or response["status_code"] != HTTP_OK

        # Handle error cases
        if expect_error:
            if response["status_code"] == HTTP_UNPROCESSABLE_ENTITY:
                return  # 422 is expected for invalid input
            elif response["status_code"] == HTTP_OK:
                response_data = response["data"]
                if "error" in response_data:
                    self.validate_error_response(response_data)
                else:
                    pytest.fail("Expected error but got successful response")
            else:
                pytest.fail(
                    f"Unexpected status code {response['status_code']} for error case"
                )

        # Handle success cases
        else:
            assert response["status_code"] == HTTP_OK
            response_data = response["data"]

            if "error" in response_data:
                pytest.fail(f"Expected success but got error: {response_data['error']}")
            else:
                self.validate_success_response(response_data)

                if not allow_empty_result:
                    assert (
                        response_data["title"].strip()
                        or len(response_data["ingredients"]) > 0
                    ), "Recipe should have either a title or ingredients"

    def test_server_health(self, server: str) -> None:
        """Test that the server is running and healthy."""
        response = requests.get(f"{server}/api/v1/", timeout=5)
        logger.info(f"Health check response: {response.status_code}")
        assert response.status_code == HTTP_OK
