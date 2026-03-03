from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import recipes
from app.core.config import settings
from app.core.dependencies import get_recipe_preview_service


PREVIEW_PATH = f"{settings.API_BASE_PATH}/recipes/preview-from-url"


class FakeRecipePreviewService:
    def __init__(
        self,
        preview: dict | None = None,
        error: str | None = None,
    ):
        self.preview = preview or {
            "source_url": "https://www.example.com/recipes/lemon-pasta",
            "target_instruction": "Extract full recipe content.",
            "raw_scraped_text": "Messy recipe text",
            "cleaned_text": "Clean recipe text",
            "recipe": {
                "title": "Lemon Pasta",
                "ingredients": ["200g pasta", "1 lemon", "2 tbsp olive oil"],
                "instructions": ["Boil pasta", "Mix lemon and oil", "Combine"],
                "servings": "2",
                "total_time": "20 minutes",
            },
            "extraction_error": None,
            "evidence": "Recipe card content",
            "confidence": 0.84,
            "trace_steps": 3,
        }
        self.error = error
        self.calls: list[dict] = []

    async def preview_from_url(
        self,
        start_url: str,
        target_instruction: str,
        max_steps: int = 10,
        max_actions_per_step: int = 2,
    ) -> tuple[dict | None, str | None]:
        self.calls.append(
            {
                "start_url": start_url,
                "target_instruction": target_instruction,
                "max_steps": max_steps,
                "max_actions_per_step": max_actions_per_step,
            }
        )
        if self.error:
            return None, self.error
        return self.preview, None


def build_client(preview_service: FakeRecipePreviewService) -> TestClient:
    app = FastAPI()
    app.include_router(recipes.router)
    app.dependency_overrides[get_recipe_preview_service] = lambda: preview_service
    return TestClient(app)


def test_preview_recipe_from_url_returns_preview_and_save_payload() -> None:
    service = FakeRecipePreviewService()
    client = build_client(service)

    response = client.post(
        PREVIEW_PATH,
        json={
            "start_url": "https://www.example.com/recipes/lemon-pasta",
            "target_instruction": "Find and extract the complete recipe.",
            "max_steps": 8,
            "max_actions_per_step": 2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["preview"]["recipe"]["title"] == "Lemon Pasta"
    assert payload["save_payload"] == {"raw_input": "Clean recipe text"}

    assert service.calls == [
        {
            "start_url": "https://www.example.com/recipes/lemon-pasta",
            "target_instruction": "Find and extract the complete recipe.",
            "max_steps": 8,
            "max_actions_per_step": 2,
        }
    ]


def test_preview_recipe_from_url_supports_target_prompt_alias() -> None:
    service = FakeRecipePreviewService()
    client = build_client(service)

    response = client.post(
        PREVIEW_PATH,
        json={
            "start_url": "https://www.example.com/recipes/lemon-pasta",
            "target_prompt": "Extract recipe text from this page.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert (
        service.calls[0]["target_instruction"] == "Extract recipe text from this page."
    )


def test_preview_recipe_from_url_returns_error_payload() -> None:
    service = FakeRecipePreviewService(
        error="auto-browse is not installed. Install and configure it before using URL preview."
    )
    client = build_client(service)

    response = client.post(
        PREVIEW_PATH,
        json={
            "start_url": "https://www.example.com/recipes/lemon-pasta",
            "target_instruction": "Extract recipe text from this page.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == (
        "auto-browse is not installed. Install and configure it before using URL preview."
    )


def test_preview_recipe_from_url_rejects_malformed_url() -> None:
    service = FakeRecipePreviewService()
    client = build_client(service)

    response = client.post(
        PREVIEW_PATH,
        json={
            "start_url": "not-a-url",
            "target_instruction": "Extract recipe text from this page.",
        },
    )

    assert response.status_code == 422
