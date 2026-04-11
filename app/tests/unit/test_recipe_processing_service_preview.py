import socket

import app.services.recipe_processing_service as recipe_processing_service_module
from app.api.schemas import Recipe
from app.services.recipe_processing_service import (
    MAX_EXTRACTED_TEXT_CHARS,
    RecipeProcessingService,
)


class EchoCleanupService:
    def cleanup_input(self, messy_input: str) -> str:
        return messy_input


class MarkerRecipeExtractor:
    def extract_recipe_from_raw_text(self, raw_text: str):
        if "MAGIC_RECIPE" not in raw_text:
            return None, "missing marker"
        return (
            Recipe(
                title="Recovered Recipe",
                ingredients=["1 marker"],
                instructions=["Use marker"],
                servings="1",
                total_time="1 minute",
            ),
            None,
        )


class PreviewServiceHarness(RecipeProcessingService):
    def __init__(self, html: str):
        super().__init__(
            cleanup_service=EchoCleanupService(),
            extractor_service=MarkerRecipeExtractor(),
            recipe_manager=object(),
            embeddings_service=object(),
            dedupe_service=object(),
        )
        self._html = html

    def _fetch_raw_html(self, source_url: str):  # type: ignore[override]
        del source_url
        return self._html


def test_cleanup_input_skips_llm_for_structured_recipe_text() -> None:
    class FailingCleanupService:
        def cleanup_input(self, messy_input: str) -> str:
            del messy_input
            raise AssertionError(
                "cleanup_input should not be called for structured text"
            )

    service = RecipeProcessingService(
        cleanup_service=FailingCleanupService(),
        extractor_service=MarkerRecipeExtractor(),
        recipe_manager=object(),
        embeddings_service=object(),
        dedupe_service=object(),
    )

    cleaned = service._cleanup_input(
        "Simple Pasta\n\nIngredients:\n- 200g pasta\n- 1 cup tomato sauce\n\n"
        "Instructions:\n1. Boil pasta\n2. Add sauce\n"
    )

    assert cleaned is not None
    assert "Simple Pasta" in cleaned


def test_cleanup_input_uses_cleanup_service_for_html_payload() -> None:
    class RecordingCleanupService:
        def __init__(self) -> None:
            self.calls = 0

        def cleanup_input(self, messy_input: str) -> str:
            self.calls += 1
            return f"CLEANED::{messy_input[:20]}"

    cleanup_service = RecordingCleanupService()
    service = RecipeProcessingService(
        cleanup_service=cleanup_service,
        extractor_service=MarkerRecipeExtractor(),
        recipe_manager=object(),
        embeddings_service=object(),
        dedupe_service=object(),
    )

    cleaned = service._cleanup_input(
        "<div>Simple Pasta</div><div>Ingredients: pasta</div><div>Instructions: boil</div>"
    )

    assert cleanup_service.calls == 1
    assert cleaned is not None
    assert cleaned.startswith("CLEANED::")


def test_preview_fails_when_recipe_is_beyond_max_context_window() -> None:
    long_noise = "noise " * 6000
    html = (
        "<html><body>"
        f"<div>{long_noise}</div>"
        "<div>MAGIC_RECIPE Ingredients: marker Instructions: use marker</div>"
        "</body></html>"
    )
    service = PreviewServiceHarness(html)

    recipe, error, diagnostics = service.preview_recipe_from_url("https://example.com")

    assert recipe is None
    assert error == "Recipe extraction failed: missing marker"
    assert diagnostics["extracted_text_length"] <= MAX_EXTRACTED_TEXT_CHARS
    assert diagnostics["cleaned_text_length"] > 0


def test_preview_skips_fallback_when_first_pass_succeeds() -> None:
    html = (
        "<html><body>"
        "<div>MAGIC_RECIPE Ingredients: marker Instructions: use marker</div>"
        "</body></html>"
    )
    service = PreviewServiceHarness(html)

    recipe, error, diagnostics = service.preview_recipe_from_url("https://example.com")

    assert error is None
    assert recipe is not None
    assert recipe.title == "Recovered Recipe"
    assert diagnostics["cleaned_text_length"] > 0


def test_validate_outbound_url_blocks_loopback_ip_literal() -> None:
    service = RecipeProcessingService(
        cleanup_service=EchoCleanupService(),
        extractor_service=MarkerRecipeExtractor(),
        recipe_manager=object(),
        embeddings_service=object(),
        dedupe_service=object(),
    )

    validated_url, error = service._validate_outbound_url("http://127.0.0.1/recipe")

    assert validated_url is None
    assert error is not None
    assert "Blocked IP target" in error


def test_validate_outbound_url_blocks_private_resolved_ip(monkeypatch) -> None:
    service = RecipeProcessingService(
        cleanup_service=EchoCleanupService(),
        extractor_service=MarkerRecipeExtractor(),
        recipe_manager=object(),
        embeddings_service=object(),
        dedupe_service=object(),
    )

    def _private_resolution(hostname: str, port: int, type: int):
        del hostname, type
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.8", port))]

    monkeypatch.setattr(socket, "getaddrinfo", _private_resolution)

    validated_url, error = service._validate_outbound_url("https://example.com/recipe")

    assert validated_url is None
    assert error is not None
    assert "Blocked resolved IP" in error


def test_validate_outbound_url_allows_public_resolved_ip(monkeypatch) -> None:
    service = RecipeProcessingService(
        cleanup_service=EchoCleanupService(),
        extractor_service=MarkerRecipeExtractor(),
        recipe_manager=object(),
        embeddings_service=object(),
        dedupe_service=object(),
    )

    def _public_resolution(hostname: str, port: int, type: int):
        del hostname, type
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", _public_resolution)

    validated_url, error = service._validate_outbound_url("https://example.com/recipe")

    assert validated_url == "https://example.com/recipe"
    assert error is None


def test_fetch_raw_html_revalidates_redirect_target(monkeypatch) -> None:
    service = RecipeProcessingService(
        cleanup_service=EchoCleanupService(),
        extractor_service=MarkerRecipeExtractor(),
        recipe_manager=object(),
        embeddings_service=object(),
        dedupe_service=object(),
    )

    class _RedirectResponse:
        status_code = 302
        headers = {"location": "http://127.0.0.1/private"}
        text = ""

        def raise_for_status(self) -> None:
            return None

    class _FakeClient:
        def __init__(self):
            self.calls: list[str] = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

        def get(self, url: str):
            self.calls.append(url)
            return _RedirectResponse()

    fake_client = _FakeClient()
    monkeypatch.setattr(
        recipe_processing_service_module.httpx,
        "Client",
        lambda **kwargs: fake_client,
    )

    def _public_resolution(hostname: str, port: int, type: int):
        del type
        if hostname == "example.com":
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))
            ]
        raise AssertionError(f"Unexpected hostname resolution call: {hostname}")

    monkeypatch.setattr(socket, "getaddrinfo", _public_resolution)

    html = service._fetch_raw_html("https://example.com/start")

    assert html is None
    assert fake_client.calls == ["https://example.com/start"]
