from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import recipes
from app.api.v1.helpers.recipe_pagination import RecipePaginationCursor
from app.core.config import settings
from app.core.dependencies import get_recipe_manager

RECIPE_ONE = "11111111-1111-1111-1111-111111111111"
RECIPE_TWO = "22222222-2222-2222-2222-222222222222"
LIST_RECIPES_PATH = f"{settings.API_BASE_PATH}/recipes/"


def _build_recipe(recipe_id: str, title: str, created_at: datetime) -> dict:
    return {
        "id": recipe_id,
        "title": title,
        "servings": "2",
        "total_time": "20 minutes",
        "source_url": "https://example.com/recipe",
        "is_public": True,
        "created_by_user_id": None,
        "is_test_data": False,
        "created_at": created_at,
        "updated_at": created_at,
    }


class FakeRecipeManager:
    def __init__(
        self,
        recipes_page: list[dict] | None = None,
        error: Exception | None = None,
    ):
        self.recipes_page = recipes_page or []
        self.error = error
        self.calls: list[dict] = []

    def list_recipes_page(
        self,
        limit: int = 50,
        cursor_created_at: datetime | None = None,
        cursor_id: str | None = None,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> list[dict]:
        self.calls.append(
            {
                "limit": limit,
                "cursor_created_at": cursor_created_at,
                "cursor_id": cursor_id,
                "include_test_data": include_test_data,
                "viewer_user_id": viewer_user_id,
            }
        )
        if self.error:
            raise self.error
        return self.recipes_page


def build_client(recipe_manager: FakeRecipeManager) -> TestClient:
    app = FastAPI()
    app.include_router(recipes.router)
    app.dependency_overrides[get_recipe_manager] = lambda: recipe_manager
    return TestClient(app)


def test_list_recipes_uses_default_limit() -> None:
    created_at = datetime(2026, 3, 1, 12, 30, 0)
    manager = FakeRecipeManager(
        recipes_page=[_build_recipe(RECIPE_ONE, "Tomato Pasta", created_at)]
    )
    client = build_client(manager)

    response = client.get(LIST_RECIPES_PATH)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["count"] == 1
    assert body["limit"] == 50
    assert body["cursor"] is None
    assert body["next_cursor"] is None
    assert body["has_more"] is False
    assert body["recipes"][0]["id"] == RECIPE_ONE
    assert manager.calls == [
        {
            "limit": 51,
            "cursor_created_at": None,
            "cursor_id": None,
            "include_test_data": False,
            "viewer_user_id": None,
        }
    ]


def test_list_recipes_returns_next_cursor_when_more_results_exist() -> None:
    created_at = datetime(2026, 3, 1, 12, 30, 0)
    manager = FakeRecipeManager(
        recipes_page=[
            _build_recipe(RECIPE_ONE, "Tomato Pasta", created_at),
            _build_recipe(RECIPE_TWO, "Lentil Soup", datetime(2026, 3, 1, 12, 0, 0)),
        ]
    )
    client = build_client(manager)

    response = client.get(LIST_RECIPES_PATH, params={"limit": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["has_more"] is True
    assert body["recipes"][0]["id"] == RECIPE_ONE
    assert isinstance(body["next_cursor"], str)

    decoded_created_at, decoded_id = RecipePaginationCursor.decode(body["next_cursor"])
    assert decoded_created_at == created_at
    assert decoded_id == RECIPE_ONE
    assert manager.calls == [
        {
            "limit": 2,
            "cursor_created_at": None,
            "cursor_id": None,
            "include_test_data": False,
            "viewer_user_id": None,
        }
    ]


def test_list_recipes_passes_decoded_cursor_to_manager() -> None:
    cursor_created_at = datetime(2026, 3, 1, 9, 0, 0)
    cursor = RecipePaginationCursor.encode(cursor_created_at, RECIPE_ONE)
    manager = FakeRecipeManager(recipes_page=[])
    client = build_client(manager)

    response = client.get(
        LIST_RECIPES_PATH,
        params={"limit": 25, "cursor": cursor},
    )

    assert response.status_code == 200
    assert manager.calls == [
        {
            "limit": 26,
            "cursor_created_at": cursor_created_at,
            "cursor_id": RECIPE_ONE,
            "include_test_data": False,
            "viewer_user_id": None,
        }
    ]


def test_list_recipes_rejects_invalid_cursor() -> None:
    manager = FakeRecipeManager()
    client = build_client(manager)

    response = client.get(LIST_RECIPES_PATH, params={"cursor": "not-a-valid-cursor"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid cursor value"
    assert manager.calls == []


def test_list_recipes_returns_500_when_manager_errors() -> None:
    manager = FakeRecipeManager(error=RuntimeError("database unavailable"))
    client = build_client(manager)

    response = client.get(LIST_RECIPES_PATH)

    assert response.status_code == 500
    assert response.json()["detail"] == "Error listing recipes"


def test_list_recipes_forwards_viewer_user_id_header() -> None:
    created_at = datetime(2026, 3, 1, 12, 30, 0)
    manager = FakeRecipeManager(
        recipes_page=[_build_recipe(RECIPE_ONE, "Tomato Pasta", created_at)]
    )
    client = build_client(manager)

    response = client.get(
        LIST_RECIPES_PATH,
        headers={"X-Viewer-User-Id": "33333333-3333-3333-3333-333333333333"},
    )

    assert response.status_code == 200
    assert manager.calls[0]["viewer_user_id"] == "33333333-3333-3333-3333-333333333333"
