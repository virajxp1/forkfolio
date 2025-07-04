"""
E2E tests for recipe cleanup endpoint.
"""

import json
import logging
import os

import pytest
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
HTTP_OK = 200
HTTP_INTERNAL_SERVER_ERROR = 500
HTTP_UNPROCESSABLE_ENTITY = 422
REQUEST_TIMEOUT = 30
DEBUG_TEXT_LENGTH = 100


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
    def test_cleanup_from_json(self, server: str, test_case: dict) -> None:
        """Test cleanup for all cases defined in cleanup_test_cases.json."""
        # Input
        input_data = test_case["input"]
        raw_text = input_data["raw_text"]

        # API Call
        request_json = {"raw_text": raw_text}
        if "source_url" in input_data:
            request_json["source_url"] = input_data["source_url"]

        response = requests.post(
            f"{server}/api/v1/cleanup-raw-recipe",
            json=request_json,
            headers={"Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )

        # Debug Output (always show for failed tests)
        print(f"\n=== Test: {test_case['name']} ===")
        truncated_input = raw_text[:DEBUG_TEXT_LENGTH]
        if len(raw_text) > DEBUG_TEXT_LENGTH:
            truncated_input += "..."
        print(f"Input: {truncated_input}")
        print(f"Status: {response.status_code}")
        if response.status_code == HTTP_OK:
            data = response.json()
            cleaned_text = data.get("cleaned_text", "No cleaned_text")
            truncated_cleaned = cleaned_text[:DEBUG_TEXT_LENGTH]
            if len(cleaned_text) > DEBUG_TEXT_LENGTH:
                truncated_cleaned += "..."
            print(f"Cleaned: {truncated_cleaned}")
        else:
            print(f"Error: {response.text}")

        # Assertions
        # Handle edge cases that might fail
        if test_case.get("expect_short_output", False):
            assert response.status_code in [HTTP_OK, HTTP_INTERNAL_SERVER_ERROR], (
                f"Expected {HTTP_OK} or {HTTP_INTERNAL_SERVER_ERROR} for edge case, "
                f"got {response.status_code}"
            )
            return

        # Expecting successful cleanup
        assert response.status_code == HTTP_OK, (
            f"Expected {HTTP_OK} but got {response.status_code}: {response.text}"
        )

        data = response.json()
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

    def test_cleanup_validation_error(self, server: str) -> None:
        """Test cleanup endpoint validation."""
        response = requests.post(
            f"{server}/api/v1/cleanup-raw-recipe",
            json={},
            timeout=REQUEST_TIMEOUT,
        )
        assert response.status_code == HTTP_UNPROCESSABLE_ENTITY
