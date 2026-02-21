"""
Base client class for API testing.
"""

import requests
import os
from typing import Any, Dict, Optional

from app.tests.utils.constants import REQUEST_TIMEOUT


class BaseAPIClient:
    """Base class for all API clients."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.timeout = REQUEST_TIMEOUT
        self.auth_token = os.getenv("API_AUTH_TOKEN", "")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request and return standardized response format.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            json_data: JSON payload for POST requests
            headers: HTTP headers

        Returns:
            Dict with 'status_code', 'data', and 'text' keys
        """
        url = f"{self.base_url}{endpoint}"
        default_headers = {"Content-Type": "application/json"}
        if self.auth_token:
            default_headers["X-API-Token"] = self.auth_token
        if headers:
            default_headers.update(headers)

        response = requests.request(
            method=method,
            url=url,
            json=json_data,
            params=params,
            headers=default_headers,
            timeout=self.timeout,
        )

        # Don't raise for status - let tests handle different status codes
        return {
            "status_code": response.status_code,
            "data": (
                response.json()
                if response.headers.get("content-type", "").startswith(
                    "application/json"
                )
                else None
            ),
            "text": response.text,
        }

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make a GET request."""
        return self._make_request("GET", endpoint, params=params, headers=headers)

    def post(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make a POST request."""
        return self._make_request(
            "POST",
            endpoint,
            json_data=json_data,
            params=params,
            headers=headers,
        )

    def put(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make a PUT request."""
        return self._make_request(
            "PUT",
            endpoint,
            json_data=json_data,
            params=params,
            headers=headers,
        )

    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make a DELETE request."""
        return self._make_request("DELETE", endpoint, params=params, headers=headers)
