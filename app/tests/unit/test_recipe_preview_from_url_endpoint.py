from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import recipes
from app.core.config import settings
from app.core.dependencies import get_recipe_preview_service

PREVIEW_PATH = f"{settings.API_BASE_PATH}/recipes/preview-from-url"


class FakePreviewService:
    def __init__(self, preview: dict | None = None, error: str | None = None):
        self.preview = preview or {"cleaned_text": "Clean recipe text"}
        self.error = error

    async def preview_from_url(self, **kwargs):
        if self.error:
            return None, self.error
        return self.preview, None


def _client(service: FakePreviewService) -> TestClient:
    app = FastAPI()
    app.include_router(recipes.router)
    app.dependency_overrides[get_recipe_preview_service] = lambda: service
    return TestClient(app)


def test_preview_endpoint_success() -> None:
    response = _client(FakePreviewService()).post(
        PREVIEW_PATH,
        json={
            "start_url": "https://www.example.com/recipes/lemon-pasta",
            "target_prompt": "Extract recipe text from this page.",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["save_payload"]["raw_input"] == "Clean recipe text"


def test_preview_endpoint_error_payload() -> None:
    response = _client(FakePreviewService(error="URL scrape failed: timeout")).post(
        PREVIEW_PATH,
        json={
            "start_url": "https://www.example.com/recipes/lemon-pasta",
            "target_instruction": "Extract recipe text from this page.",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["error"] == "URL scrape failed: timeout"


def test_preview_endpoint_rejects_malformed_url() -> None:
    response = _client(FakePreviewService()).post(
        PREVIEW_PATH,
        json={
            "start_url": "not-a-url",
            "target_instruction": "Extract recipe text from this page.",
        },
    )
    assert response.status_code == 422
