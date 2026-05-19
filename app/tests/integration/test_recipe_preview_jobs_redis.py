import importlib
import json
import os
import time

import pytest
import redis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.schemas import Recipe
from app.core.config import settings

PREVIEW_JOB_CREATE_PATH = f"{settings.API_BASE_PATH}/recipes/preview-from-url/jobs"
REDIS_KEY_PREFIX = "forkfolio:recipe_preview_job:"


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


def _delete_prefixed_keys(client: redis.Redis, prefix: str) -> None:
    keys = list(client.scan_iter(f"{prefix}*"))
    if keys:
        client.delete(*keys)


def _redis_client_from_env() -> redis.Redis:
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        pytest.skip("REDIS_URL not set; skipping Redis-backed preview job integration test.")

    client = redis.Redis.from_url(redis_url, decode_responses=True)
    deadline = time.monotonic() + 10
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            client.ping()
            return client
        except Exception as exc:  # pragma: no cover - only hit on infra startup issues
            last_error = exc
            time.sleep(0.25)

    raise RuntimeError(f"Redis did not become ready within 10s: {last_error}")


@pytest.fixture
def redis_client() -> redis.Redis:
    client = _redis_client_from_env()
    _delete_prefixed_keys(client, REDIS_KEY_PREFIX)
    yield client
    _delete_prefixed_keys(client, REDIS_KEY_PREFIX)


def _build_client(service: FakeRecipeProcessingService) -> tuple[TestClient, object]:
    import app.api.v1.endpoints.recipes as recipes_module
    import app.core.dependencies as dependencies_module
    import app.core.job_store as job_store_module
    import app.core.redis_client as redis_client_module
    import app.services.recipe_preview_job_service as preview_job_service_module

    importlib.reload(redis_client_module)
    importlib.reload(job_store_module)
    importlib.reload(preview_job_service_module)
    importlib.reload(dependencies_module)
    recipes_module = importlib.reload(recipes_module)

    app = FastAPI()
    app.include_router(recipes_module.router)
    app.dependency_overrides[dependencies_module.get_recipe_processing_service] = (
        lambda: service
    )
    return TestClient(app), job_store_module.recipe_preview_job_store


def test_preview_job_endpoints_persist_state_in_redis(redis_client: redis.Redis) -> None:
    processing_service = FakeRecipeProcessingService(
        recipe=Recipe(
            title="Tomato Pasta",
            ingredients=["200g spaghetti", "2 tomatoes"],
            instructions=["Boil pasta", "Toss with tomatoes"],
            servings="2",
            total_time="20 minutes",
        ),
        diagnostics={"scrapegraphai_success": 1},
    )

    create_client, job_store = _build_client(processing_service)
    assert job_store.__class__.__name__ == "RedisJobStore"

    create_response = create_client.post(
        PREVIEW_JOB_CREATE_PATH,
        json={"url": "https://example.com/tomato-pasta"},
    )

    assert create_response.status_code == 202
    create_payload = create_response.json()
    assert create_payload["status"] == "queued"
    assert create_payload["url"] == "https://example.com/tomato-pasta"
    assert processing_service.calls == ["https://example.com/tomato-pasta"]

    job_id = create_payload["job_id"]
    redis_key = f"{REDIS_KEY_PREFIX}{job_id}"
    raw_job = redis_client.get(redis_key)
    assert raw_job is not None
    redis_payload = json.loads(raw_job)
    assert redis_payload["job_id"] == job_id
    assert redis_payload["url"] == "https://example.com/tomato-pasta"

    create_client.close()

    poll_client, _ = _build_client(FakeRecipeProcessingService())

    deadline = time.monotonic() + 5
    status_payload: dict | None = None
    while time.monotonic() < deadline:
        status_response = poll_client.get(f"{PREVIEW_JOB_CREATE_PATH}/{job_id}")
        assert status_response.status_code == 200
        status_payload = status_response.json()
        if status_payload["status"] in {"completed", "failed"}:
            break
        time.sleep(0.1)

    assert status_payload is not None
    assert status_payload["status"] == "completed"
    assert status_payload["success"] is True
    assert status_payload["recipe_preview"]["title"] == "Tomato Pasta"
    assert status_payload["diagnostics"]["scrapegraphai_success"] == 1

    persisted_job = json.loads(redis_client.get(redis_key) or "{}")
    assert persisted_job["status"] == "completed"
    assert persisted_job["recipe_preview"]["title"] == "Tomato Pasta"
    assert "completed_at" in persisted_job

    poll_client.close()
