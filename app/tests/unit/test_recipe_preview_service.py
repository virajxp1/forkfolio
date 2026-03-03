import asyncio
import socket
import sys
from types import SimpleNamespace

from app.core.config import settings
from app.services.recipe_preview_service import RecipePreviewService


def _addrinfo(ip: str):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]


def test_validate_external_url_rejects_non_http_scheme() -> None:
    error = RecipePreviewService._validate_external_url("ftp://example.com/recipe")
    assert error == "start_url must use http or https."


def test_validate_external_url_rejects_loopback_ip_literal() -> None:
    error = RecipePreviewService._validate_external_url("http://127.0.0.1/recipe")
    assert error == "start_url resolves to a blocked address."


def test_validate_external_url_rejects_private_dns_resolution(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: _addrinfo("10.10.10.10"),
    )
    error = RecipePreviewService._validate_external_url("https://example.com/recipe")
    assert error == "start_url resolves to a blocked address."


def test_validate_external_url_accepts_public_dns_resolution(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: _addrinfo("93.184.216.34"),
    )
    error = RecipePreviewService._validate_external_url("https://example.com/recipe")
    assert error is None


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
