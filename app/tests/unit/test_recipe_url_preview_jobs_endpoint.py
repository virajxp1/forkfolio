import multiprocessing

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.schemas import Recipe
from app.api.v1.endpoints import recipes
from app.core.cache import recipe_preview_job_cache
from app.core.config import settings
from app.core.dependencies import (
    get_recipe_preview_job_service,
    get_recipe_processing_service,
)
from app.core.job_store import JobStoreUnavailableError
from app.services.recipe_preview_job_service import RecipePreviewJobService

PREVIEW_JOB_CREATE_PATH = f"{settings.API_BASE_PATH}/recipes/preview-from-url/jobs"
WORKER_CONTEXT = multiprocessing.get_context("fork")


class FakeRecipeProcessingService:
    def __init__(
        self,
        recipe: Recipe | None = None,
        error: str | None = None,
        diagnostics: dict[str, int] | None = None,
    ) -> None:
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
    app.dependency_overrides[get_recipe_preview_job_service] = lambda: (
        RecipePreviewJobService(
            processing_service=service,
            worker_context=WORKER_CONTEXT,
        )
    )
    return TestClient(app)


class UnavailablePreviewJobService:
    def create_job(self, source_url: str) -> dict:
        del source_url
        raise JobStoreUnavailableError("boom")

    def get_job(self, job_id: str) -> dict:
        del job_id
        raise JobStoreUnavailableError("boom")

    def process_job(self, *args, **kwargs) -> None:
        del args, kwargs


def build_client_with_preview_service(
    service: FakeRecipeProcessingService,
    preview_job_service: UnavailablePreviewJobService,
) -> TestClient:
    app = FastAPI()
    app.include_router(recipes.router)
    app.dependency_overrides[get_recipe_processing_service] = lambda: service
    app.dependency_overrides[get_recipe_preview_job_service] = lambda: (
        preview_job_service
    )
    return TestClient(app)


def setup_function() -> None:
    recipe_preview_job_cache.clear()


def test_create_preview_recipe_job_returns_queued_then_completed_status() -> None:
    fake_service = FakeRecipeProcessingService(
        recipe=Recipe(
            title="Tomato Pasta",
            ingredients=["200g spaghetti", "2 tomatoes"],
            instructions=["Boil pasta", "Toss with tomatoes"],
            servings="2",
            total_time="20 minutes",
        ),
        diagnostics={"scrapegraphai_success": 1},
    )
    client = build_client(fake_service)

    response = client.post(
        PREVIEW_JOB_CREATE_PATH,
        json={"url": "https://example.com/tomato-pasta"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["url"] == "https://example.com/tomato-pasta"

    status_response = client.get(f"{PREVIEW_JOB_CREATE_PATH}/{payload['job_id']}")

    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["status"] == "completed"
    assert status_payload["success"] is True
    assert status_payload["recipe_preview"]["title"] == "Tomato Pasta"


def test_create_preview_recipe_job_returns_failed_status() -> None:
    fake_service = FakeRecipeProcessingService(
        recipe=None,
        error="Failed to fetch recipe webpage",
        diagnostics={"scrapegraphai_attempted": 1},
    )
    client = build_client(fake_service)

    response = client.post(
        PREVIEW_JOB_CREATE_PATH,
        json={"url": "https://example.com/unavailable"},
    )

    assert response.status_code == 202
    payload = response.json()

    status_response = client.get(f"{PREVIEW_JOB_CREATE_PATH}/{payload['job_id']}")

    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["status"] == "failed"
    assert status_payload["success"] is False
    assert status_payload["error"] == "Failed to fetch recipe webpage"


def test_get_preview_recipe_job_returns_404_for_unknown_job() -> None:
    client = build_client(FakeRecipeProcessingService())

    response = client.get(f"{PREVIEW_JOB_CREATE_PATH}/missing-job")

    assert response.status_code == 404
    assert response.json() == {"detail": "Recipe preview job not found or expired."}


def test_create_preview_recipe_job_returns_503_when_job_store_unavailable() -> None:
    client = build_client_with_preview_service(
        FakeRecipeProcessingService(),
        UnavailablePreviewJobService(),
    )

    response = client.post(
        PREVIEW_JOB_CREATE_PATH,
        json={"url": "https://example.com/tomato-pasta"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Recipe preview job store unavailable."}


def test_get_preview_recipe_job_returns_503_when_job_store_unavailable() -> None:
    client = build_client_with_preview_service(
        FakeRecipeProcessingService(),
        UnavailablePreviewJobService(),
    )

    response = client.get(f"{PREVIEW_JOB_CREATE_PATH}/any-job")

    assert response.status_code == 503
    assert response.json() == {"detail": "Recipe preview job store unavailable."}
