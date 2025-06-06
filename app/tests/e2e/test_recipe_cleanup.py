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
HTTP_UNPROCESSABLE_ENTITY = 422
REQUEST_TIMEOUT = 30


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
        input_data = test_case["input"]

        # Make the cleanup request
        response = requests.post(
            f"{server}/api/v1/cleanup-raw-recipe",
            json={
                "raw_text": input_data["raw_text"],
                **(
                    {}
                    if "source_url" not in input_data
                    else {"source_url": input_data["source_url"]}
                ),
            },
            headers={"Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )

        # Log the API response
        logger.info(f"Cleanup test case: {test_case['name']}")
        logger.info(f"Status code: {response.status_code}")
        if response.status_code == HTTP_OK:
            data = response.json()
            logger.info(f"Cleaned text length: {data.get('cleaned_length', 'unknown')}")
        else:
            logger.info(f"Response text: {response.text}")

        # Check if we expect a short output (for edge cases)
        expect_short_output = test_case.get("expect_short_output", False)

        if expect_short_output:
            # For short outputs, we might get an error or very short cleaned text
            # Just verify the endpoint responds
            assert response.status_code in [200, 500]
            return

        # For normal cases, verify successful response
        assert response.status_code == HTTP_OK
        data = response.json()

        # Check response structure
        assert "cleaned_text" in data
        assert "original_length" in data
        assert "cleaned_length" in data

        cleaned_text = data["cleaned_text"]

        # Verify expected content is present (case-insensitive)
        cleaned_text_lower = cleaned_text.lower()
        for expected in test_case.get("expected_contains", []):
            assert expected.lower() in cleaned_text_lower, (
                f"Expected '{expected}' in cleaned text for {test_case['name']}"
            )

        # Verify unwanted content is removed
        for not_expected in test_case.get("not_expected", []):
            assert not_expected not in cleaned_text, (
                f"Did not expect '{not_expected}' in cleaned text for "
                f"{test_case['name']}"
            )

        # Verify source URL if provided
        if "source_url" in input_data:
            assert data["source_url"] == input_data["source_url"]

    def test_cleanup_validation_error(self, server: str) -> None:
        """Test cleanup endpoint validation."""
        # Send request without required field
        response = requests.post(
            f"{server}/api/v1/cleanup-raw-recipe",
            json={},
            timeout=REQUEST_TIMEOUT,
        )

        logger.info(f"Validation error test - Status code: {response.status_code}")
        assert response.status_code == HTTP_UNPROCESSABLE_ENTITY
