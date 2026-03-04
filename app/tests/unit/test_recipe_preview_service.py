import asyncio
from types import SimpleNamespace

from app.services.recipe_preview_service import RecipePreviewService


class FakeAutoBrowseClient:
    def __init__(self, payload: dict | None = None, error: str | None = None):
        self.payload = payload
        self.error = error

    def run(self, **kwargs) -> tuple[dict | None, str | None]:
        return self.payload, self.error


class FakeCleanupService:
    def cleanup_input(self, raw_input: str) -> str:
        return raw_input.strip()


class FakeExtractorService:
    def extract_recipe_from_raw_text(self, cleaned_text: str):
        return SimpleNamespace(model_dump=lambda: {"title": "Example"}), None


def test_preview_from_url_success() -> None:
    service = RecipePreviewService(
        auto_browse_client=FakeAutoBrowseClient(
            payload={
                "structured_data": {"raw_recipe_text": " Recipe text "},
                "source_url": "https://example.com/recipe",
                "trace": [],
            }
        ),
        cleanup_service=FakeCleanupService(),
        extractor_service=FakeExtractorService(),
    )
    preview, error = asyncio.run(
        service.preview_from_url(
            start_url="https://example.com/recipe",
            target_instruction="Extract recipe",
        )
    )
    assert error is None
    assert preview is not None
    assert preview["raw_scraped_text"] == "Recipe text"
    assert preview["recipe"]["title"] == "Example"


def test_preview_from_url_propagates_client_error() -> None:
    service = RecipePreviewService(
        auto_browse_client=FakeAutoBrowseClient(error="URL scrape failed: timeout"),
        cleanup_service=FakeCleanupService(),
        extractor_service=FakeExtractorService(),
    )
    preview, error = asyncio.run(
        service.preview_from_url(
            start_url="https://example.com/recipe",
            target_instruction="Extract recipe",
        )
    )
    assert preview is None
    assert error == "URL scrape failed: timeout"


def test_preview_from_url_rejects_empty_prompt() -> None:
    service = RecipePreviewService(
        auto_browse_client=FakeAutoBrowseClient(payload={"answer": "unused"}),
        cleanup_service=FakeCleanupService(),
        extractor_service=FakeExtractorService(),
    )
    preview, error = asyncio.run(
        service.preview_from_url(
            start_url="https://example.com/recipe",
            target_instruction="   ",
        )
    )
    assert preview is None
    assert error == "target_instruction cannot be empty."
