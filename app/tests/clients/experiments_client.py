"""
Client for Experiments router endpoints.
Maps to: app/api/v1/endpoints/experiments.py
"""

from typing import Any, Dict, Optional

from app.core.config import settings

from .base_client import BaseAPIClient


class ExperimentsClient(BaseAPIClient):
    """Client for experiment thread and message endpoints."""

    BASE_ENDPOINT = f"{settings.API_V1_STR}/experiments"
    THREADS_ENDPOINT = f"{BASE_ENDPOINT}/threads"

    def create_thread(
        self,
        mode: str = "invent_new",
        title: Optional[str] = None,
        context_recipe_ids: Optional[list[str]] = None,
        include_test_data: bool = True,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "mode": mode,
            "include_test_data": include_test_data,
        }
        if title is not None:
            payload["title"] = title
        if context_recipe_ids is not None:
            payload["context_recipe_ids"] = context_recipe_ids
        return self.post(self.THREADS_ENDPOINT, json_data=payload)

    def list_threads(self, limit: int = 20) -> Dict[str, Any]:
        return self.get(self.THREADS_ENDPOINT, params={"limit": limit})

    def get_thread(
        self,
        thread_id: str,
        message_limit: int = 120,
        include_test_data: bool = True,
    ) -> Dict[str, Any]:
        endpoint = f"{self.THREADS_ENDPOINT}/{thread_id}"
        return self.get(
            endpoint,
            params={
                "message_limit": message_limit,
                "include_test_data": include_test_data,
            },
        )

    def create_message(
        self,
        thread_id: str,
        content: str,
        context_recipe_ids: Optional[list[str]] = None,
        attach_recipe_ids: Optional[list[str]] = None,
        include_test_data: bool = True,
    ) -> Dict[str, Any]:
        endpoint = f"{self.THREADS_ENDPOINT}/{thread_id}/messages"
        payload: Dict[str, Any] = {
            "content": content,
            "include_test_data": include_test_data,
        }
        if context_recipe_ids is not None:
            payload["context_recipe_ids"] = context_recipe_ids
        if attach_recipe_ids is not None:
            payload["attach_recipe_ids"] = attach_recipe_ids
        return self.post(endpoint, json_data=payload)

    def stream_message(
        self,
        thread_id: str,
        content: str,
        context_recipe_ids: Optional[list[str]] = None,
        attach_recipe_ids: Optional[list[str]] = None,
        include_test_data: bool = True,
    ) -> Dict[str, Any]:
        endpoint = f"{self.THREADS_ENDPOINT}/{thread_id}/messages/stream"
        payload: Dict[str, Any] = {
            "content": content,
            "include_test_data": include_test_data,
        }
        if context_recipe_ids is not None:
            payload["context_recipe_ids"] = context_recipe_ids
        if attach_recipe_ids is not None:
            payload["attach_recipe_ids"] = attach_recipe_ids
        return self.post(
            endpoint,
            json_data=payload,
            headers={"Accept": "text/event-stream"},
        )
