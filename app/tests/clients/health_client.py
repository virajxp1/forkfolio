"""
Client for Health router endpoints.
Maps to: app/routers/health.py
"""

from typing import Dict, Any
from .base_client import BaseAPIClient
from app.core.config import settings


class HealthClient(BaseAPIClient):
    """Client for health-related endpoints."""

    # Endpoint paths - centralized in one place
    ROOT_ENDPOINT = f"{settings.API_V1_STR}/"
    HEALTH_ENDPOINT = f"{settings.API_V1_STR}/health"

    def get_root(self) -> Dict[str, Any]:
        """
        Get API root welcome message.

        Endpoint: GET /api/v1/
        Router: app.routers.health:root
        """
        return self.get(self.ROOT_ENDPOINT)

    def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check including database connectivity.

        Endpoint: GET /api/v1/health
        Router: app.routers.health:health_check
        """
        return self.get(self.HEALTH_ENDPOINT)
