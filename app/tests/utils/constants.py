"""Shared constants for tests."""

import os

# HTTP Status Codes
HTTP_OK = 200
HTTP_NOT_FOUND = 404
HTTP_UNPROCESSABLE_ENTITY = 422

# Test Configuration
REQUEST_TIMEOUT = int(os.getenv("TEST_REQUEST_TIMEOUT_SECONDS", "90"))
DEBUG_TEXT_LENGTH = 100
