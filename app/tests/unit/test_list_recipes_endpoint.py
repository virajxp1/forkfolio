from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import recipes
from app.core.config import settings
from app.core.dependencies import get_recipe_manager

LIST_RECIPES_PATH = f"{settings.API_BASE_PATH}/recipes/"


class FakeRecipeManager:
    def __init__(
        self,
        rows: list[dict] | None = None,
        should_raise: bool = False,
    ):
        self.rows = rows or []
        self.should_raise = should_raise
        self.calls: list[int] = []

    def list_recipes(self, limit: int = 200) -> list[dict]:
        self.calls.append(limit)
        if self.should_raise:
            raise RuntimeError("boom")
        return self.rows


def build_client(manager: FakeRecipeManager) -> TestClient:
    app = FastAPI()
    app.include_router(recipes.router)
    app.dependency_overrides[get_recipe_manager] = lambda: manager
    return TestClient(app)


def test_list_recipes_returns_alpha_ordered_rows() -> None:
    manager = FakeRecipeManager(
        rows=[
            {
                "id": "r2",
                "title": "Apple Pie",
                "servings": "6",
                "total_time": "45 minutes",
                "source_url": None,
                "is_test_data": False,
                "created_at": None,
                "updated_at": None,
            },
            {
                "id": "r1",
                "title": "Banana Bread",
                "servings": "8",
                "total_time": "60 minutes",
                "source_url": None,
                "is_test_data": False,
                "created_at": None,
                "updated_at": None,
            },
        ]
    )
    client = build_client(manager)

    response = client.get(f"{LIST_RECIPES_PATH}?limit=75")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["count"] == 2
    assert [recipe["title"] for recipe in body["recipes"]] == [
        "Apple Pie",
        "Banana Bread",
    ]
    assert manager.calls == [75]


def test_list_recipes_returns_500_on_manager_failure() -> None:
    manager = FakeRecipeManager(should_raise=True)
    client = build_client(manager)

    response = client.get(LIST_RECIPES_PATH)

    assert response.status_code == 500
    assert response.json()["detail"] == "Error listing recipes"
