"""E2E coverage for preview-from-url endpoint behavior."""

from app.tests.clients.api_client import APIClient
from app.tests.utils.constants import HTTP_OK, HTTP_UNPROCESSABLE_ENTITY


def test_preview_from_url_blocks_loopback_target(api_client: APIClient) -> None:
    response = api_client.recipes.preview_recipe_from_url("http://127.0.0.1/recipe")

    assert response["status_code"] == HTTP_OK
    payload = response["data"]
    assert payload["success"] is False
    assert payload["created"] is False
    assert payload["url"] == "http://127.0.0.1/recipe"
    assert payload["error"] == "Failed to fetch raw HTML from URL"


def test_preview_from_url_rejects_invalid_url(api_client: APIClient) -> None:
    response = api_client.recipes.preview_recipe_from_url("not-a-url")
    assert response["status_code"] == HTTP_UNPROCESSABLE_ENTITY
