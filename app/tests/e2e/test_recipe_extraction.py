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
INPUT_PREVIEW_LENGTH = 100


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
        missing_fields = [
            field for field in required_fields if field not in response_data
        ]
        if missing_fields:
            pytest.fail(
                f"Missing required fields: {missing_fields}. "
                f"Response data: {response_data}"
            )

        # Basic type validation with detailed error messages
        title = response_data.get("title")
        if not isinstance(title, str):
            pytest.fail(
                f"Title should be a string, got {type(title).__name__}: {title}"
            )

        ingredients = response_data.get("ingredients")
        if not isinstance(ingredients, list):
            pytest.fail(
                f"Ingredients should be a list, "
                f"got {type(ingredients).__name__}: {ingredients}"
            )

        instructions = response_data.get("instructions")
        if not isinstance(instructions, list):
            pytest.fail(
                f"Instructions should be a list, "
                f"got {type(instructions).__name__}: {instructions}"
            )

        servings = response_data.get("servings")
        if not isinstance(servings, str):
            pytest.fail(
                f"Servings should be a string, "
                f"got {type(servings).__name__}: {servings}"
            )

        total_time = response_data.get("total_time")
        if not isinstance(total_time, str):
            pytest.fail(
                f"Total time should be a string, "
                f"got {type(total_time).__name__}: {total_time}"
            )

    def validate_error_response(self, response_data: dict[str, Any]) -> None:
        """Validate an error response."""
        if "error" not in response_data:
            pytest.fail(
                f"Error response should have 'error' field. "
                f"Response data: {response_data}"
            )

        if response_data.get("success") is not False:
            pytest.fail(
                f"Error responses should have success=false. "
                f"Response data: {response_data}"
            )

        error_msg = response_data.get("error")
        if not isinstance(error_msg, str):
            pytest.fail(
                f"Error should be a string, got {type(error_msg).__name__}: {error_msg}"
            )

    def _log_test_failure(
        self, test_name: str, test_case: dict, response: dict, reason: str
    ) -> None:
        """Log detailed test failure information."""
        print(f"\n❌ TEST FAILURE: {test_name}")
        print(f"   Reason: {reason}")
        print(f"   Expected error: {test_case.get('expect_error', False)}")
        print(f"   Allow empty: {test_case.get('allow_empty_result', False)}")
        input_text = test_case["input_text"]
        preview = (
            f"{input_text[:INPUT_PREVIEW_LENGTH]}..."
            if len(input_text) > INPUT_PREVIEW_LENGTH
            else input_text
        )
        print(f"   Input: {preview}")
        print(f"   Response status: {response.get('status_code', 'MISSING')}")
        print(
            f"   Response data: {json.dumps(response.get('data', 'MISSING'), indent=2)}"
        )

    def _handle_error_case(
        self, response: dict, test_name: str, test_case: dict
    ) -> None:
        """Handle test cases that expect errors."""
        if response["status_code"] == HTTP_UNPROCESSABLE_ENTITY:
            print("   ✅ Rejected (422)")
            # 422 is the expected behavior for invalid input
        elif response["status_code"] == HTTP_OK:
            response_data = response["data"]
            if "error" in response_data:
                print(f"   ✅ Error: {response_data['error']}")
                self.validate_error_response(response_data)
            else:
                print("   ⚠️  Expected error but got success")
                self.validate_success_response(response_data)
                self._log_test_failure(
                    test_name,
                    test_case,
                    response,
                    "Expected error but got successful response",
                )
                pytest.fail("Expected error but got successful response")
        else:
            pytest.fail(
                f"Unexpected status code {response['status_code']} for error case"
            )

    def _handle_success_case(
        self, response: dict, test_name: str, test_case: dict
    ) -> None:
        """Handle test cases that expect success."""
        assert response["status_code"] == HTTP_OK, (
            f"Expected 200, got {response['status_code']}: {response['text']}"
        )

        response_data = response["data"]
        allow_empty_result = test_case.get("allow_empty_result", False)

        if "error" in response_data:
            print(f"   ❌ Error: {response_data['error']}")
            self.validate_error_response(response_data)
            self._log_test_failure(
                test_name,
                test_case,
                response,
                f"Expected success but got error: {response_data['error']}",
            )
            pytest.fail("Expected success but got error")
        else:
            print("   ✅ Success:")
            print(f"{json.dumps(response_data, indent=2)}")
            self.validate_success_response(response_data)

            if not allow_empty_result:
                assert (
                    response_data["title"].strip()
                    or len(response_data["ingredients"]) > 0
                ), "Recipe should have either a title or ingredients"

    @pytest.mark.parametrize(
        "test_case", [pytest.param(case, id=case["name"]) for case in load_test_cases()]
    )
    def test_recipe_extraction_from_json(
        self, api_client: APIClient, test_case: dict
    ) -> None:
        """Test recipe extraction for all cases defined in test_cases.json."""
        test_name = test_case["name"]
        expect_error = test_case.get("expect_error", False)

        print(f"\n🧪 {test_name}: {test_case.get('description', 'No description')}")

        try:
            response = api_client.extract_recipe(test_case["input_text"])
        except Exception as e:
            self._log_test_failure(test_name, test_case, {}, f"API call failed: {e}")
            raise

        # Validate basic response structure
        if "status_code" not in response:
            pytest.fail(f"API response missing status_code: {response}")
        if "data" not in response and response["status_code"] == HTTP_OK:
            pytest.fail(f"API response missing data for 200 response: {response}")

        # Handle different expected outcomes based on test case configuration
        if expect_error:
            self._handle_error_case(response, test_name, test_case)
        else:
            self._handle_success_case(response, test_name, test_case)

    def test_server_health(self, server: str) -> None:
        """Test that the server is running and healthy."""
        print("\n🏥 Server health check")
        response = requests.get(f"{server}/api/v1/", timeout=5)
        assert response.status_code == HTTP_OK, "Server health check failed"
        print("   ✅ Healthy")
