import os

import pytest

from app.tests.clients.api_client import APIClient
from app.tests.utils.constants import HTTP_OK


def test_preview_from_url_then_save(api_client: APIClient) -> None:
    recipe_url = os.getenv("RECIPE_PREVIEW_TEST_URL", "").strip()
    if not recipe_url:
        pytest.skip("Set RECIPE_PREVIEW_TEST_URL to run URL preview e2e.")

    preview_response = api_client.recipes.preview_recipe_from_url(
        start_url=recipe_url,
        target_instruction="Extract full recipe text. Do not summarize.",
    )
    assert preview_response["status_code"] == HTTP_OK
    preview_data = preview_response["data"]
    assert preview_data.get("success") is True, preview_data.get("error")

    cleaned_text = str(((preview_data.get("preview") or {}).get("cleaned_text") or ""))
    assert cleaned_text.strip()

    save_response = api_client.recipes.process_and_store_recipe(
        cleaned_text,
        enforce_deduplication=False,
    )
    assert save_response["status_code"] == HTTP_OK
    save_data = save_response["data"]
    assert save_data.get("success") is True, save_data.get("error")
