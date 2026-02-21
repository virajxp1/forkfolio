"""
Client for Recipes router endpoints.
Maps to: app/routers/recipes.py

This contains the main recipe functionality endpoints.
"""

from urllib.parse import urlencode
from typing import Any, Dict, Optional

from app.core.config import settings
from .base_client import BaseAPIClient


class RecipesClient(BaseAPIClient):
    """Client for main recipe functionality endpoints."""

    # Endpoint paths - centralized in one place
    PROCESS_AND_STORE_ENDPOINT = f"{settings.API_V1_STR}/recipes/process-and-store"
    SEMANTIC_SEARCH_ENDPOINT = f"{settings.API_V1_STR}/recipes/search/semantic"

    def process_and_store_recipe(
        self,
        raw_input: str,
        is_test: bool = True,
        enforce_deduplication: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Complete recipe processing pipeline: the main end-to-end recipe endpoint.

        1. Cleanup raw input
        2. Extract structured recipe data
        3. Store in database
        4. Return database ID

        Endpoint: POST /api/v1/recipes/process-and-store
        Router: app.routers.recipes:process_and_store_recipe
        """
        payload = {"raw_input": raw_input, "isTest": is_test}
        if enforce_deduplication is not None:
            payload["enforce_deduplication"] = enforce_deduplication
        return self.post(self.PROCESS_AND_STORE_ENDPOINT, json_data=payload)

    def get_recipe(self, recipe_id: str) -> Dict[str, Any]:
        """
        Get a complete recipe by its UUID.

        Endpoint: GET /api/v1/recipes/{recipe_id}
        Router: app.routers.recipes:get_recipe
        """
        endpoint = f"{settings.API_V1_STR}/recipes/{recipe_id}"
        return self.get(endpoint)

    def get_recipe_all(self, recipe_id: str) -> Dict[str, Any]:
        """
        Get a complete recipe by its UUID, including embeddings.

        Endpoint: GET /api/v1/recipes/{recipe_id}/all
        Router: app.routers.recipes:get_recipe_all
        """
        endpoint = f"{settings.API_V1_STR}/recipes/{recipe_id}/all"
        return self.get(endpoint)

    def delete_recipe(self, recipe_id: str) -> Dict[str, Any]:
        """
        Delete a recipe by its UUID.

        Endpoint: DELETE /api/v1/recipes/delete/{recipe_id}
        Router: app.routers.recipes:delete_recipe
        """
        endpoint = f"{settings.API_V1_STR}/recipes/delete/{recipe_id}"
        return self.delete(endpoint)

    def search_semantic(
        self,
        query: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Semantic search over recipes using vector similarity.

        Endpoint: GET /api/v1/recipes/search/semantic
        Router: app.api.v1.endpoints.recipes:semantic_search_recipes
        """
        query_string = urlencode(
            {
                "query": query,
                "limit": limit,
            }
        )
        endpoint = f"{self.SEMANTIC_SEARCH_ENDPOINT}?{query_string}"
        return self.get(endpoint)
