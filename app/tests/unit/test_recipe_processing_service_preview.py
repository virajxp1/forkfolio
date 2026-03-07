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
