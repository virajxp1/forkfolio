import asyncio

from app.services.recipe_preview_service import RecipePreviewService


class FakeAutoBrowseClient:
    def __init__(self, response_payload: dict | None = None, error: str | None = None):
        self.response_payload = response_payload
        self.error = error
        self.calls: list[dict] = []

    def run(
        self,
        *,
        start_url: str,
        target_prompt: str,
        max_steps: int,
        max_actions_per_step: int,
        extraction_schema: dict[str, str] | None = None,
    ) -> tuple[dict | None, str | None]:
        self.calls.append(
            {
                "start_url": start_url,
                "target_prompt": target_prompt,
                "max_steps": max_steps,
                "max_actions_per_step": max_actions_per_step,
                "extraction_schema": extraction_schema,
            }
        )
        return self.response_payload, self.error


def test_scrape_recipe_text_maps_client_response_with_missing_trace() -> None:
    fake_client = FakeAutoBrowseClient(
        response_payload={
            "answer": None,
            "structured_data": {"raw_recipe_text": "Recipe text"},
            "source_url": "https://example.com/recipe",
            "evidence": "recipe card",
            "confidence": 0.8,
            "trace": None,
        }
    )
    service = RecipePreviewService(auto_browse_client=fake_client)

    payload, error = asyncio.run(
        service._scrape_recipe_text(
            start_url="https://example.com/recipe",
            target_instruction="Extract recipe",
            max_steps=5,
            max_actions_per_step=2,
        )
    )

    assert error is None
    assert payload is not None
    assert payload["raw_scraped_text"] == "Recipe text"
    assert payload["source_url"] == "https://example.com/recipe"
    assert payload["trace_steps"] == 0
    assert fake_client.calls[0]["target_prompt"] == "Extract recipe"


def test_scrape_recipe_text_propagates_client_error() -> None:
    fake_client = FakeAutoBrowseClient(
        response_payload=None,
        error="URL scrape failed: max_steps_exceeded",
    )
    service = RecipePreviewService(auto_browse_client=fake_client)

    payload, error = asyncio.run(
        service._scrape_recipe_text(
            start_url="https://example.com/recipe",
            target_instruction="Extract recipe",
            max_steps=5,
            max_actions_per_step=2,
        )
    )

    assert payload is None
    assert error == "URL scrape failed: max_steps_exceeded"


def test_scrape_recipe_text_requires_non_empty_instruction() -> None:
    fake_client = FakeAutoBrowseClient(
        response_payload={"answer": "should not be used"},
    )
    service = RecipePreviewService(auto_browse_client=fake_client)

    payload, error = asyncio.run(
        service._scrape_recipe_text(
            start_url="https://example.com/recipe",
            target_instruction="   ",
            max_steps=5,
            max_actions_per_step=2,
        )
    )

    assert payload is None
    assert error == "target_instruction cannot be empty."
    assert fake_client.calls == []
