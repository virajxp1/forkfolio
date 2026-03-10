"""Shared constants for tests."""

import os

from app.core.config import settings

# HTTP Status Codes
HTTP_OK = 200
HTTP_NOT_FOUND = 404
HTTP_UNPROCESSABLE_ENTITY = 422

# Test Configuration
# Keep test client timeout above server request timeout so tests can observe
# server-generated timeout responses instead of client read timeouts.
REQUEST_TIMEOUT = int(
    os.getenv(
        "TEST_REQUEST_TIMEOUT_SECONDS",
        str(int(settings.REQUEST_TIMEOUT_SECONDS) + 5),
    )
)
DEBUG_TEXT_LENGTH = 100
