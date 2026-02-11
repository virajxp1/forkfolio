"""
Shared fixtures for E2E tests.
"""

import atexit
import os
import subprocess
import sys
import time
from collections.abc import Generator
from typing import Optional

import pytest
import requests

from app.tests.utils.constants import HTTP_OK
from app.tests.clients.health_client import HealthClient
from app.tests.clients.api_client import APIClient

DEFAULT_PORT = 8000
MAX_RETRIES = 30
REQUIRED_LIVE_TEST_ENV_VARS = ("SUPABASE_PASSWORD", "OPEN_ROUTER_API_KEY")


class ServerManager:
    """Manages server lifecycle for e2e tests."""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None

    def start_server(self, port: int, project_root: str) -> None:
        """Start the test server."""
        self.process = subprocess.Popen(
            [sys.executable, "scripts/start_test_server.py", str(port)],
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


@pytest.fixture(scope="session", autouse=True)
def server() -> Generator[str, None, None]:
    """Start the server once for all tests and clean up afterwards."""
    missing_vars = [
        variable for variable in REQUIRED_LIVE_TEST_ENV_VARS if not os.getenv(variable)
    ]
    if missing_vars:
        missing_message = (
            "Missing required environment variables for live E2E tests: "
            f"{', '.join(missing_vars)}"
        )
        if os.getenv("CI"):
            pytest.fail(missing_message)
        pytest.skip(f"{missing_message}. Skipping live E2E suite.")

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
    health_client = HealthClient(base_url)
    max_retries = MAX_RETRIES
    for _ in range(max_retries):
        try:
            response = health_client.get_root()
            if response["status_code"] == HTTP_OK:
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
    """Provide a centralized API client for all E2E tests."""
    return APIClient(server)
