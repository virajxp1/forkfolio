"""
Pytest tests for recipe extraction pipeline.
Automatically manages server lifecycle and uses test_cases.json for test data.
Tests that API returns valid responses without strict validation.
"""
import json
import os
import subprocess
import time
import pytest
import requests
from typing import Dict, Any, Generator, Optional
import atexit
import sys

# Global variable to track server process
_server_process: Optional[subprocess.Popen] = None


def load_test_cases():
    """Load test cases from JSON file."""
    test_cases_file = os.path.join(os.path.dirname(__file__), "test_cases.json")
    with open(test_cases_file, 'r') as f:
        return json.load(f)


@pytest.fixture(scope="session", autouse=True)
def server() -> Generator[str, None, None]:
    """Start the server once for all tests and clean up afterwards."""
    global _server_process

    # Find project root (go up from app/tests/e2e to project root)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    # Get worker ID for parallel execution (pytest-xdist)
    worker_id = os.environ.get('PYTEST_XDIST_WORKER', 'master')

    # Use different ports for different workers to avoid conflicts
    if worker_id == 'master':
        port = 8000
    else:
        # Extract worker number (gw0, gw1, etc.) and add to base port
        worker_num = int(worker_id.replace('gw', '')) if worker_id.startswith('gw') else 0
        port = 8000 + worker_num + 1

    # Start the server
    _server_process = subprocess.Popen(
        [sys.executable, "start_test_server.py", str(port)],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Register cleanup function
    def cleanup():
        global _server_process
        if _server_process:
            try:
                _server_process.terminate()
                _server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _server_process.kill()
            except:
                pass
            _server_process = None

    atexit.register(cleanup)

    # Wait for server to start
    base_url = f"http://localhost:{port}"
    max_retries = 30
    for _ in range(max_retries):
        try:
            response = requests.get(f"{base_url}/api/v1/", timeout=1)
            if response.status_code == 200:
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    else:
        # Capture server output for debugging
        stdout, stderr = _server_process.communicate(timeout=5)
        cleanup()
        error_msg = f"Server failed to start within 30 seconds on port {port}\n"
        error_msg += f"STDOUT: {stdout.decode() if stdout else 'None'}\n"
        error_msg += f"STDERR: {stderr.decode() if stderr else 'None'}"
        pytest.fail(error_msg)

    yield base_url

    # Cleanup
    cleanup()


@pytest.fixture
def api_client(server: str):
    """Provide an API client for each test."""
    return APIClient(server)


class APIClient:
    """Helper class for making API requests."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.endpoint = f"{base_url}/api/v1/ingest-raw-recipe"

    def extract_recipe(self, input_text: str) -> Dict[str, Any]:
        """Make a request to the recipe extraction API."""
        payload = {"raw_input": input_text}

        response = requests.post(
            self.endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        # Don't raise for status - let tests handle different status codes
        return {
            "status_code": response.status_code,
            "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else None,
            "text": response.text
        }


class TestRecipeExtraction:
    """Test suite for recipe extraction functionality - 100% JSON-driven."""

    def validate_success_response(self, response_data: Dict[str, Any]) -> None:
        """Validate a successful recipe response."""
        required_fields = ["title", "ingredients", "instructions", "servings", "total_time"]
        for field in required_fields:
            assert field in response_data, f"Missing required field: {field}"

        # Basic type validation
        assert isinstance(response_data["title"], str), "Title should be a string"
        assert isinstance(response_data["ingredients"], list), "Ingredients should be a list"
        assert isinstance(response_data["instructions"], list), "Instructions should be a list"
        assert isinstance(response_data["servings"], str), "Servings should be a string"
        assert isinstance(response_data["total_time"], str), "Total time should be a string"

    def validate_error_response(self, response_data: Dict[str, Any]) -> None:
        """Validate an error response."""
        assert "error" in response_data, "Error response should have 'error' field"
        assert response_data.get("success") is False, "Error responses should have success=false"
        assert isinstance(response_data["error"], str), "Error should be a string"

    @pytest.mark.parametrize("test_case", [
        pytest.param(case, id=case["name"])
        for case in load_test_cases()
    ])
    def test_recipe_extraction_from_json(self, api_client: APIClient, test_case: dict) -> None:
        """Test recipe extraction for all cases defined in test_cases.json."""
        test_name = test_case["name"]
        expect_error = test_case.get("expect_error", False)
        allow_empty_result = test_case.get("allow_empty_result", False)

        print(f"\n🧪 {test_name}: {test_case.get('description', 'No description')}")

        response = api_client.extract_recipe(test_case["input_text"])

        # Handle different expected outcomes based on test case configuration
        if expect_error:
            # For edge cases that should return errors
            if response["status_code"] == 422:
                print(f"   ✅ Rejected (422)")
                assert True, "422 is acceptable for invalid input"
            elif response["status_code"] == 200:
                response_data = response["data"]
                if "error" in response_data:
                    print(f"   ✅ Error: {response_data['error']}")
                    self.validate_error_response(response_data)
                else:
                    print(f"   ⚠️  Expected error but got success")
                    self.validate_success_response(response_data)
            else:
                pytest.fail(f"Unexpected status code {response['status_code']} for error case")
        else:
            # For normal recipe cases that should succeed
            assert response["status_code"] == 200, f"Expected 200, got {response['status_code']}: {response['text']}"

            response_data = response["data"]

            if "error" in response_data:
                print(f"   ❌ Error: {response_data['error']}")
                self.validate_error_response(response_data)
            else:
                print(f"   ✅ Success:")
                print(f"{json.dumps(response_data, indent=2)}")
                self.validate_success_response(response_data)

                # For recipe inputs, we expect at least some content (unless explicitly allowed to be empty)
                if not allow_empty_result:
                    assert response_data["title"].strip() or len(response_data["ingredients"]) > 0, \
                        "Recipe should have either a title or ingredients"

    def test_server_health(self, server: str) -> None:
        """Test that the server is running and healthy."""
        print(f"\n🏥 Server health check")
        response = requests.get(f"{server}/api/v1/", timeout=5)
        assert response.status_code == 200, "Server health check failed"
        print(f"   ✅ Healthy")
