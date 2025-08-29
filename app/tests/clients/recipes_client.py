"""
Client for Recipes router endpoints.
Maps to: app/routers/recipes.py

This contains the main recipe functionality endpoints.
"""

from typing import Dict, Any
from .base_client import BaseAPIClient
from app.core.config import settings


class RecipesClient(BaseAPIClient):
    """Client for main recipe functionality endpoints."""

    # Endpoint paths - centralized in one place
    PROCESS_AND_STORE_ENDPOINT = f"{settings.API_V1_STR}/recipes/process-and-store"

    def process_and_store_recipe(self, raw_input: str) -> Dict[str, Any]:
        """
        Complete recipe processing pipeline: the main end-to-end recipe endpoint.

        1. Cleanup raw input
        2. Extract structured recipe data
        3. Store in database
        4. Return database ID

        Endpoint: POST /api/v1/recipes/process-and-store
        Router: app.routers.recipes:process_and_store_recipe
        """
        payload = {"raw_input": raw_input}
        return self.post(self.PROCESS_AND_STORE_ENDPOINT, json_data=payload)

    def get_recipe(self, recipe_id: str) -> Dict[str, Any]:
        """
        Get a complete recipe by its UUID.

        Endpoint: GET /api/v1/recipes/{recipe_id}
        Router: app.routers.recipes:get_recipe
        """
        endpoint = f"{settings.API_V1_STR}/recipes/{recipe_id}"
        return self.get(endpoint)
