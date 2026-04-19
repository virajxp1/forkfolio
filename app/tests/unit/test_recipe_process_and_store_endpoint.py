from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import recipes
from app.core.config import settings
from app.core.dependencies import get_recipe_manager, get_recipe_processing_service

PROCESS_AND_STORE_PATH = f"{settings.API_BASE_PATH}/recipes/process-and-store"
RECIPE_ID = "11111111-1111-1111-1111-111111111111"
SOURCE_URL = "https://example.com/tomato-pasta"


class FakeRecipeProcessingService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def process_raw_recipe(
        self,
        raw_input: str,
        source_url: str | None = None,
        enforce_deduplication: bool = True,
        is_test: bool = False,
        is_public: bool = True,
        created_by_user_id: str | None = None,
    ) -> tuple[str, None, bool]:
        self.calls.append(
            {
                "raw_input": raw_input,
                "source_url": source_url,
                "enforce_deduplication": enforce_deduplication,
                "is_test": is_test,
                "is_public": is_public,
                "created_by_user_id": created_by_user_id,
            }
        )
        return RECIPE_ID, None, True


class FakeRecipeManager:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def get_full_recipe(
        self,
        recipe_id: str,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> dict:
        self.calls.append(
            {
                "recipe_id": recipe_id,
                "include_test_data": include_test_data,
                "viewer_user_id": viewer_user_id,
            }
        )
        return {
            "id": recipe_id,
            "title": "Tomato Pasta",
            "servings": "2",
            "total_time": "20 minutes",
            "source_url": SOURCE_URL,
            "is_public": True,
            "created_by_user_id": None,
            "created_at": None,
            "updated_at": None,
            "ingredients": ["200g spaghetti"],
            "instructions": ["Boil pasta"],
            "embeddings": [],
        }


def build_client(
    processing_service: FakeRecipeProcessingService,
    recipe_manager: FakeRecipeManager,
) -> TestClient:
    app = FastAPI()
    app.include_router(recipes.router)
    app.dependency_overrides[get_recipe_processing_service] = lambda: processing_service
    app.dependency_overrides[get_recipe_manager] = lambda: recipe_manager
    return TestClient(app)


def test_process_and_store_forwards_source_url() -> None:
    processing_service = FakeRecipeProcessingService()
    recipe_manager = FakeRecipeManager()
    client = build_client(processing_service, recipe_manager)

    response = client.post(
        PROCESS_AND_STORE_PATH,
        json={
            "raw_input": "Tomato Pasta recipe with ingredients and instructions.",
            "source_url": SOURCE_URL,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["recipe_id"] == RECIPE_ID
    assert processing_service.calls == [
        {
            "raw_input": "Tomato Pasta recipe with ingredients and instructions.",
            "source_url": SOURCE_URL,
            "enforce_deduplication": True,
            "is_test": False,
            "is_public": True,
            "created_by_user_id": None,
        }
    ]
    assert recipe_manager.calls == [
        {"recipe_id": RECIPE_ID, "include_test_data": False, "viewer_user_id": None}
    ]


def test_process_and_store_accepts_source_url_alias() -> None:
    processing_service = FakeRecipeProcessingService()
    recipe_manager = FakeRecipeManager()
    client = build_client(processing_service, recipe_manager)

    response = client.post(
        PROCESS_AND_STORE_PATH,
        json={
            "raw_input": "Tomato Pasta recipe with ingredients and instructions.",
            "sourceUrl": SOURCE_URL,
        },
    )

    assert response.status_code == 200
    assert processing_service.calls[0]["source_url"] == SOURCE_URL
    assert processing_service.calls[0]["is_public"] is True


def test_process_and_store_returns_test_recipe_when_requested() -> None:
    processing_service = FakeRecipeProcessingService()
    recipe_manager = FakeRecipeManager()
    client = build_client(processing_service, recipe_manager)

    response = client.post(
        PROCESS_AND_STORE_PATH,
        json={
            "raw_input": "Tomato Pasta recipe with ingredients and instructions.",
            "isTest": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["created"] is True
    assert body["recipe_id"] == RECIPE_ID
    assert body["recipe"]["id"] == RECIPE_ID
    assert processing_service.calls[0]["is_test"] is True
    assert recipe_manager.calls == [
        {"recipe_id": RECIPE_ID, "include_test_data": True, "viewer_user_id": None}
    ]


def test_process_and_store_forwards_visibility_and_creator() -> None:
    processing_service = FakeRecipeProcessingService()
    recipe_manager = FakeRecipeManager()
    client = build_client(processing_service, recipe_manager)

    response = client.post(
        PROCESS_AND_STORE_PATH,
        json={
            "raw_input": "Tomato Pasta recipe with ingredients and instructions.",
            "isPublic": False,
            "createdByUserId": "22222222-2222-2222-2222-222222222222",
        },
    )

    assert response.status_code == 200
    assert processing_service.calls[0]["is_public"] is False
    assert (
        processing_service.calls[0]["created_by_user_id"]
        == "22222222-2222-2222-2222-222222222222"
    )
    assert recipe_manager.calls == [
        {
            "recipe_id": RECIPE_ID,
            "include_test_data": False,
            "viewer_user_id": "22222222-2222-2222-2222-222222222222",
        }
    ]
