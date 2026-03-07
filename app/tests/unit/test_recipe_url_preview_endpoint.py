from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.schemas import Recipe
from app.api.v1.endpoints import recipes
from app.core.config import settings
from app.core.dependencies import get_recipe_processing_service

PREVIEW_FROM_URL_PATH = f"{settings.API_BASE_PATH}/recipes/preview-from-url"


class FakeRecipeProcessingService:
    def __init__(
        self,
        recipe: Recipe | None = None,
        error: str | None = None,
        diagnostics: dict[str, int] | None = None,
    ):
        self.recipe = recipe
        self.error = error
        self.diagnostics = diagnostics or {}
        self.calls: list[str] = []

    def preview_recipe_from_url(
        self, source_url: str
    ) -> tuple[Recipe | None, str | None, dict[str, int]]:
        self.calls.append(source_url)
        return self.recipe, self.error, self.diagnostics


def build_client(service: FakeRecipeProcessingService) -> TestClient:
    app = FastAPI()
    app.include_router(recipes.router)
    app.dependency_overrides[get_recipe_processing_service] = lambda: service
    return TestClient(app)


def test_preview_recipe_from_url_returns_recipe_preview() -> None:
    fake_service = FakeRecipeProcessingService(
        recipe=Recipe(
            title="Tomato Pasta",
            ingredients=["200g spaghetti", "2 tomatoes"],
            instructions=["Boil pasta", "Toss with tomatoes"],
            servings="2",
            total_time="20 minutes",
        ),
        diagnostics={
            "raw_html_length": 1000,
            "extracted_text_length": 600,
            "cleaned_text_length": 420,
        },
    )
    client = build_client(fake_service)

    response = client.post(
        PREVIEW_FROM_URL_PATH,
        json={"url": "https://example.com/tomato-pasta"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["created"] is False
    assert payload["url"] == "https://example.com/tomato-pasta"
    assert payload["recipe_preview"]["title"] == "Tomato Pasta"
    assert payload["diagnostics"]["raw_html_length"] == 1000
    assert fake_service.calls == ["https://example.com/tomato-pasta"]


def test_preview_recipe_from_url_returns_error_payload() -> None:
    fake_service = FakeRecipeProcessingService(
        recipe=None,
        error="Failed to fetch raw HTML from URL",
        diagnostics={"raw_html_length": 0},
    )
    client = build_client(fake_service)

    response = client.post(
        PREVIEW_FROM_URL_PATH,
        json={"url": "https://example.com/missing"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["created"] is False
    assert payload["url"] == "https://example.com/missing"
    assert payload["error"] == "Failed to fetch raw HTML from URL"
    assert payload["diagnostics"]["raw_html_length"] == 0


def test_preview_recipe_from_url_rejects_invalid_url() -> None:
    fake_service = FakeRecipeProcessingService()
    client = build_client(fake_service)

    response = client.post(
        PREVIEW_FROM_URL_PATH,
        json={"url": "not-a-url"},
    )

    assert response.status_code == 422
    assert fake_service.calls == []
