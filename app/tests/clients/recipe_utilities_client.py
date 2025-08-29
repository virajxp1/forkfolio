"""
Client for Recipe Utilities router endpoints.
Maps to: app/routers/recipe_utilities.py

These are temporary building block endpoints that will be deprecated.
"""

from typing import Dict, Any
from .base_client import BaseAPIClient
from app.core.config import settings


class RecipeUtilitiesClient(BaseAPIClient):
    """Client for recipe utility endpoints (temporary building blocks)."""

    # Endpoint paths - centralized in one place
    INGEST_RAW_ENDPOINT = f"{settings.API_V1_STR}/ingest-raw"
    CLEANUP_ENDPOINT = f"{settings.API_V1_STR}/cleanup"

    def extract_recipe(self, raw_input: str) -> Dict[str, Any]:
        """
        Extract structured recipe data from raw text input.

        TEMPORARY: This endpoint will be removed in future versions.
        Use RecipeClient.process_and_store_recipe for end-to-end flow.

        Endpoint: POST /api/v1/ingest-raw
        Router: app.routers.recipe_utilities:ingest_raw_recipe
        """
        payload = {"raw_input": raw_input}
        return self.post(self.INGEST_RAW_ENDPOINT, json_data=payload)

    def cleanup_recipe(self, raw_text: str, source_url: str = None) -> Dict[str, Any]:
        """
        Clean up messy recipe input data (HTML, scraped content, etc.).

        TEMPORARY: This endpoint will be removed in future versions.
        Use RecipeClient.process_and_store_recipe for end-to-end flow.

        Endpoint: POST /api/v1/cleanup
        Router: app.routers.recipe_utilities:recipe_cleanup
        """
        payload = {"raw_text": raw_text}
        if source_url:
            payload["source_url"] = source_url

        return self.post(self.CLEANUP_ENDPOINT, json_data=payload)
