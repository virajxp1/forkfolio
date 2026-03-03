"""E2E coverage for URL preview flow (preview -> save)."""

import importlib.util
import os

import pytest

from app.tests.clients.api_client import APIClient
from app.tests.utils.constants import HTTP_OK
from app.tests.utils.helpers import maybe_throttle, truncate_debug_text

DEFAULT_TARGET_INSTRUCTION = (
    "Extract the primary recipe from this page. "
    "Do not summarize. "
    "Return recipe text exactly as written and include title, servings, total time, "
    "ingredients, and instructions."
)


def test_preview_from_url_then_save(api_client: APIClient) -> None:
    if importlib.util.find_spec("auto_browse") is None:
        pytest.skip("auto-browse is not installed in the test environment.")

    recipe_url = os.getenv("RECIPE_PREVIEW_TEST_URL", "").strip()
    if not recipe_url:
        pytest.skip("Set RECIPE_PREVIEW_TEST_URL to run URL preview e2e.")
    target_instruction = os.getenv(
        "RECIPE_PREVIEW_TEST_TARGET_INSTRUCTION", DEFAULT_TARGET_INSTRUCTION
    )

    recipe_id = None
    created = False
    try:
        maybe_throttle()
        preview_response = api_client.recipes.preview_recipe_from_url(
            start_url=recipe_url,
            target_instruction=target_instruction,
            max_steps=10,
            max_actions_per_step=2,
        )

        print("\n=== URL Preview E2E ===")
        print(f"URL: {recipe_url}")
        print(f"Status: {preview_response['status_code']}")
        print(
            "Response: "
            f"{preview_response.get('data', preview_response.get('text', 'No data'))}"
        )

        assert preview_response["status_code"] == HTTP_OK
        preview_data = preview_response["data"]
        assert preview_data.get("success") is True, (
            f"Preview endpoint returned error: {preview_data.get('error')}"
        )

        preview_payload = preview_data.get("preview") or {}
        cleaned_text = str(preview_payload.get("cleaned_text") or "")
        assert cleaned_text.strip(), "Expected non-empty cleaned_text from preview"
        assert len(cleaned_text.strip()) >= 50

        save_payload = preview_data.get("save_payload") or {}
        raw_input = str(save_payload.get("raw_input") or "")
        assert raw_input.strip(), "Expected save_payload.raw_input in preview response"
        assert raw_input == cleaned_text

        maybe_throttle()
        save_response = api_client.recipes.process_and_store_recipe(
            raw_input,
            enforce_deduplication=False,
        )
        assert save_response["status_code"] == HTTP_OK, (
            f"Save failed with status {save_response['status_code']}. "
            f"Response: {save_response.get('data', save_response.get('text'))}"
        )
        save_data = save_response["data"]
        assert save_data.get("success") is True, (
            f"Expected save success but got error: {save_data.get('error')}"
        )

        recipe_id = save_data.get("recipe_id")
        assert recipe_id
        created = save_data.get("created", True)
        recipe = save_data.get("recipe") or {}
        title = str(recipe.get("title") or "")
        assert title.strip(), (
            "Saved recipe is missing a title. "
            f"cleaned_text={truncate_debug_text(cleaned_text, max_length=500)}"
        )
    finally:
        if recipe_id and created:
            api_client.recipes.delete_recipe(recipe_id)
