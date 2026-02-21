"""
Client for Recipe Books router endpoints.
Maps to: app/api/v1/endpoints/recipe_books.py
"""

from typing import Any, Dict, Optional

from app.core.config import settings

from .base_client import BaseAPIClient


class RecipeBooksClient(BaseAPIClient):
    """Client for recipe book endpoints."""

    BASE_ENDPOINT = f"{settings.API_V1_STR}/recipe-books"
    COLLECTION_ENDPOINT = f"{BASE_ENDPOINT}/"

    def create_recipe_book(
        self, name: str, description: Optional[str] = None
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"name": name}
        if description is not None:
            payload["description"] = description
        return self.post(self.COLLECTION_ENDPOINT, json_data=payload)

    def get_recipe_books(
        self, name: Optional[str] = None, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if name:
            params["name"] = name
        if limit is not None:
            params["limit"] = limit
        return self.get(self.COLLECTION_ENDPOINT, params=params if params else None)

    def get_recipe_book(self, recipe_book_id: str) -> Dict[str, Any]:
        endpoint = f"{self.BASE_ENDPOINT}/{recipe_book_id}"
        return self.get(endpoint)

    def add_recipe_to_book(self, recipe_book_id: str, recipe_id: str) -> Dict[str, Any]:
        endpoint = f"{self.BASE_ENDPOINT}/{recipe_book_id}/recipes/{recipe_id}"
        return self.put(endpoint)

    def remove_recipe_from_book(
        self, recipe_book_id: str, recipe_id: str
    ) -> Dict[str, Any]:
        endpoint = f"{self.BASE_ENDPOINT}/{recipe_book_id}/recipes/{recipe_id}"
        return self.delete(endpoint)

    def get_recipe_books_for_recipe(self, recipe_id: str) -> Dict[str, Any]:
        endpoint = f"{self.BASE_ENDPOINT}/by-recipe/{recipe_id}"
        return self.get(endpoint)

    def get_recipe_book_stats(self) -> Dict[str, Any]:
        endpoint = f"{self.BASE_ENDPOINT}/stats"
        return self.get(endpoint)
