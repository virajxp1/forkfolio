"""
Pytest tests for recipe extraction pipeline.
Automatically manages server lifecycle and uses test_cases.json for test data.
Tests that API returns valid responses without strict validation.
"""

import atexit
import json
import os
import subprocess
import sys
import time
from collections.abc import Generator
from typing import Any, Optional

import pytest
import requests

# Constants
HTTP_OK = 200
HTTP_UNPROCESSABLE_ENTITY = 422
DEFAULT_PORT = 8000
MAX_RETRIES = 30
REQUEST_TIMEOUT = 30


class ServerManager:
    """Manages server lifecycle for e2e tests."""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None

    def start_server(self, port: int, project_root: str) -> None:
        """Start the test server."""
        self.process = subprocess.Popen(
            [sys.executable, "start_test_server.py", str(port)],
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def stop_server(self) -> None:
        """Stop the test server."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception:
                pass
            finally:
                self.process = None

    def get_debug_info(self) -> tuple[Optional[str], Optional[str]]:
        """Get server output for debugging."""
        if self.process:
            stdout, stderr = self.process.communicate(timeout=5)
            return (
                stdout.decode() if stdout else None,
                stderr.decode() if stderr else None,
            )
        return None, None


def load_test_cases():
    """Load test cases from JSON file."""
    test_cases_file = os.path.join(os.path.dirname(__file__), "test_cases.json")
    with open(test_cases_file) as f:
        return json.load(f)


@pytest.fixture(scope="session", autouse=True)
def server() -> Generator[str, None, None]:
    """Start the server once for all tests and clean up afterwards."""
    server_manager = ServerManager()

    # Find project root (go up from app/tests/e2e to project root)
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    )

    # Get worker ID for parallel execution (pytest-xdist)
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")

    # Use different ports for different workers to avoid conflicts
    if worker_id == "master":
        port = DEFAULT_PORT
    else:
        # Extract worker number (gw0, gw1, etc.) and add to base port
        worker_num = (
            int(worker_id.replace("gw", "")) if worker_id.startswith("gw") else 0
        )
        port = DEFAULT_PORT + worker_num + 1

    # Start the server
    server_manager.start_server(port, project_root)

    # Register cleanup function
    atexit.register(server_manager.stop_server)

    # Wait for server to start
    base_url = f"http://localhost:{port}"
    max_retries = MAX_RETRIES
    for _ in range(max_retries):
        try:
            response = requests.get(f"{base_url}/api/v1/", timeout=1)
            if response.status_code == HTTP_OK:
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    else:
        # Capture server output for debugging
        stdout, stderr = server_manager.get_debug_info()
        server_manager.stop_server()
        error_msg = (
            f"Server failed to start within {MAX_RETRIES} seconds on port {port}\n"
        )
        error_msg += f"STDOUT: {stdout if stdout else 'None'}\n"
        error_msg += f"STDERR: {stderr if stderr else 'None'}"
        pytest.fail(error_msg)

    yield base_url

    # Cleanup
    server_manager.stop_server()


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
    """Test suite for recipe extraction functionality - 100% JSON-driven."""

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
        assert response.status_code == HTTP_OK
