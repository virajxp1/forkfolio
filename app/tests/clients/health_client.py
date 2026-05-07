"""
Client for Health router endpoints.
Maps to: app/api/v1/endpoints/health.py
"""

from typing import Dict, Any
from .base_client import BaseAPIClient
from app.core.config import settings


class HealthClient(BaseAPIClient):
    """Client for health-related endpoints."""

    # Endpoint paths - centralized in one place
    ROOT_ENDPOINT = f"{settings.API_BASE_PATH}/"
    HEALTH_ENDPOINT = f"{settings.API_BASE_PATH}/health"

    def get_root(self) -> Dict[str, Any]:
        """
        Get API root welcome message.

        Endpoint: GET /api/v1/
        Router: app.api.v1.endpoints.health:root
        """
        return self.get(self.ROOT_ENDPOINT)

    def health_check(self) -> Dict[str, Any]:
        """
        Perform lightweight liveness check.

        Endpoint: GET /api/v1/health
        Router: app.api.v1.endpoints.health:health_check
        """
        return self.get(self.HEALTH_ENDPOINT)
