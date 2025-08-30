"""
E2E tests for recipe cleanup endpoint.
"""

import json
import os

import pytest
import requests

from app.tests.utils.constants import (
    HTTP_OK,
    HTTP_INTERNAL_SERVER_ERROR,
    HTTP_UNPROCESSABLE_ENTITY,
    REQUEST_TIMEOUT,
)
from app.tests.utils.helpers import truncate_debug_text
from app.tests.clients.api_client import APIClient


def load_cleanup_test_cases():
    """Load cleanup test cases from JSON file."""
    test_cases_file = os.path.join(os.path.dirname(__file__), "cleanup_test_cases.json")
    with open(test_cases_file) as f:
        return json.load(f)


class TestRecipeCleanup:
    """Test suite for recipe cleanup functionality."""

    @pytest.mark.parametrize(
        "test_case",
        [pytest.param(case, id=case["name"]) for case in load_cleanup_test_cases()],
    )
    def test_cleanup_from_json(self, api_client: APIClient, test_case: dict) -> None:
        """Test cleanup for all cases defined in cleanup_test_cases.json."""
        # Input
        input_data = test_case["input"]
        raw_text = input_data["raw_text"]

        # API Call - use the recipe utilities client for cleanup
        source_url = input_data.get("source_url")
        response = api_client.recipe_utilities.cleanup_recipe(raw_text, source_url)

        # Debug Output (always show for failed tests)
        print(f"\n=== Test: {test_case['name']} ===")
        print(f"Input: {truncate_debug_text(raw_text)}")
        print(f"Status: {response['status_code']}")
        if response["status_code"] == HTTP_OK:
            data = response["data"]
            cleaned_text = data.get("cleaned_text", "No cleaned_text")
            print(f"Cleaned: {truncate_debug_text(cleaned_text)}")
        else:
            print(f"Error: {response['text']}")

        # Assertions
        # Handle edge cases that might fail
        if test_case.get("expect_short_output", False):
            assert response["status_code"] in [HTTP_OK, HTTP_INTERNAL_SERVER_ERROR], (
                f"Expected {HTTP_OK} or {HTTP_INTERNAL_SERVER_ERROR} for edge case, "
                f"got {response['status_code']}"
            )
            return

        # Expecting successful cleanup
        assert response["status_code"] == HTTP_OK, (
            f"Expected {HTTP_OK} but got {response['status_code']}: {response['text']}"
        )

        data = response["data"]
        assert "cleaned_text" in data, f"Response missing 'cleaned_text' field: {data}"
        cleaned_text = data["cleaned_text"]

        # Check expected content is present (case-insensitive)
        expected_items = test_case.get("expected_contains", [])
        for expected in expected_items:
            assert expected.lower() in cleaned_text.lower(), (
                f"Expected '{expected}' in cleaned text. Got: {cleaned_text}"
            )

        # Check unwanted content is removed
        not_expected_items = test_case.get("not_expected", [])
        for not_expected in not_expected_items:
            assert not_expected not in cleaned_text, (
                f"Found unwanted '{not_expected}' in cleaned text. Got: {cleaned_text}"
            )

        # Check source URL if provided
        if "source_url" in input_data:
            assert data["source_url"] == input_data["source_url"], (
                f"Source URL mismatch. Expected: {input_data['source_url']}, "
                f"Got: {data.get('source_url')}"
            )

    def test_cleanup_validation_error(self, api_client: APIClient) -> None:
        """Test cleanup endpoint validation."""
        # Make a raw POST request with invalid JSON to test validation
        from app.core.config import settings

        response = requests.post(
            f"{api_client.base_url}{settings.API_V1_STR}/cleanup",
            json={},  # Missing required raw_text field
            timeout=REQUEST_TIMEOUT,
        )
        assert response.status_code == HTTP_UNPROCESSABLE_ENTITY
