import asyncio
import sys
from types import SimpleNamespace

from app.core.config import settings
from app.services.recipe_preview_service import RecipePreviewService


def test_scrape_recipe_text_handles_missing_trace(monkeypatch) -> None:
    class FakeOpenRouterClient:
        def __init__(self, api_key: str, model_name: str):
            self.api_key = api_key
            self.model_name = model_name

    async def fake_run_agent(*args, **kwargs):
        return SimpleNamespace(
            error=None,
            answer=None,
            structured_data={"raw_recipe_text": "Recipe text"},
            source_url="https://example.com/recipe",
            evidence="recipe card",
            confidence=0.8,
            trace=None,
        )

    monkeypatch.setitem(
        sys.modules,
        "auto_browse",
        SimpleNamespace(
            OpenRouterClient=FakeOpenRouterClient,
            run_agent=fake_run_agent,
        ),
    )
    monkeypatch.setattr(settings, "OPEN_ROUTER_API_KEY", "test-key")
    monkeypatch.setattr(settings, "LLM_MODEL_NAME", "test-model")

    service = RecipePreviewService()
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
    assert payload["trace_steps"] == 0


def test_scrape_recipe_text_handles_run_agent_exception(monkeypatch) -> None:
    class FakeOpenRouterClient:
        def __init__(self, api_key: str, model_name: str):
            self.api_key = api_key
            self.model_name = model_name

    async def fake_run_agent(*args, **kwargs):
        raise RuntimeError("temporary upstream failure")

    monkeypatch.setitem(
        sys.modules,
        "auto_browse",
        SimpleNamespace(
            OpenRouterClient=FakeOpenRouterClient,
            run_agent=fake_run_agent,
        ),
    )
    monkeypatch.setattr(settings, "OPEN_ROUTER_API_KEY", "test-key")
    monkeypatch.setattr(settings, "LLM_MODEL_NAME", "test-model")

    service = RecipePreviewService()
    payload, error = asyncio.run(
        service._scrape_recipe_text(
            start_url="https://example.com/recipe",
            target_instruction="Extract recipe",
            max_steps=5,
            max_actions_per_step=2,
        )
    )

    assert payload is None
    assert error == "URL scrape failed: temporary upstream failure"


def test_scrape_recipe_text_requires_non_empty_instruction(monkeypatch) -> None:
    class FakeOpenRouterClient:
        def __init__(self, api_key: str, model_name: str):
            self.api_key = api_key
            self.model_name = model_name

    async def fake_run_agent(*args, **kwargs):
        raise AssertionError("run_agent should not be called when prompt is empty")

    monkeypatch.setitem(
        sys.modules,
        "auto_browse",
        SimpleNamespace(
            OpenRouterClient=FakeOpenRouterClient,
            run_agent=fake_run_agent,
        ),
    )
    monkeypatch.setattr(settings, "OPEN_ROUTER_API_KEY", "test-key")
    monkeypatch.setattr(settings, "LLM_MODEL_NAME", "test-model")

    service = RecipePreviewService()
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
