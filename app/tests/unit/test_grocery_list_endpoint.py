from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import recipes
from app.core.config import settings
from app.core.dependencies import (
    get_grocery_list_aggregation_service,
    get_recipe_manager,
)

RECIPE_ONE = "11111111-1111-1111-1111-111111111111"
RECIPE_TWO = "22222222-2222-2222-2222-222222222222"
RECIPE_THREE = "33333333-3333-3333-3333-333333333333"
GROCERY_LIST_PATH = f"{settings.API_BASE_PATH}/recipes/grocery-list"


class FakeRecipeManager:
    def __init__(self, ingredients_by_recipe: dict[str, list[str]] | None = None):
        self.ingredients_by_recipe = ingredients_by_recipe or {}
        self.calls: list[dict[str, object]] = []

    def get_ingredients_for_recipes(
        self,
        recipe_ids: list[str],
        include_test_data: bool = False,
    ) -> dict[str, list[str]]:
        self.calls.append(
            {
                "recipe_ids": recipe_ids,
                "include_test_data": include_test_data,
            }
        )
        return {
            recipe_id: self.ingredients_by_recipe[recipe_id]
            for recipe_id in recipe_ids
            if recipe_id in self.ingredients_by_recipe
        }


class FakeGroceryListAggregationService:
    def __init__(
        self,
        ingredients: list[str] | None = None,
        error: str | None = None,
    ):
        self.ingredients = ingredients or []
        self.error = error
        self.calls: list[list[str]] = []

    def aggregate_ingredients(
        self,
        ingredients: list[str],
    ) -> tuple[list[str] | None, str | None]:
        self.calls.append(ingredients)
        if self.error:
            return None, self.error
        return self.ingredients, None


def build_client(
    recipe_manager: FakeRecipeManager,
    grocery_service: FakeGroceryListAggregationService,
) -> TestClient:
    app = FastAPI()
    app.include_router(recipes.router)
    app.dependency_overrides[get_recipe_manager] = lambda: recipe_manager
    app.dependency_overrides[get_grocery_list_aggregation_service] = lambda: (
        grocery_service
    )
    return TestClient(app)


def test_create_grocery_list_returns_aggregated_ingredients() -> None:
    manager = FakeRecipeManager(
        ingredients_by_recipe={
            RECIPE_ONE: ["1 tomato", "2 cloves garlic"],
            RECIPE_TWO: ["1 tomato", "1 onion"],
        }
    )
    grocery_service = FakeGroceryListAggregationService(
        ingredients=["2 tomatoes", "2 cloves garlic", "1 onion"]
    )
    client = build_client(manager, grocery_service)

    response = client.post(
        GROCERY_LIST_PATH,
        json={"recipe_ids": [RECIPE_ONE, RECIPE_TWO]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["recipe_ids"] == [RECIPE_ONE, RECIPE_TWO]
    assert body["ingredients"] == ["2 tomatoes", "2 cloves garlic", "1 onion"]
    assert body["count"] == 3
    assert manager.calls == [
        {"recipe_ids": [RECIPE_ONE, RECIPE_TWO], "include_test_data": False}
    ]
    assert grocery_service.calls == [
        ["1 tomato", "2 cloves garlic", "1 tomato", "1 onion"]
    ]


def test_create_grocery_list_deduplicates_recipe_ids_before_loading() -> None:
    manager = FakeRecipeManager(
        ingredients_by_recipe={
            RECIPE_ONE: ["1 tomato"],
            RECIPE_TWO: ["1 onion"],
        }
    )
    grocery_service = FakeGroceryListAggregationService(
        ingredients=["1 tomato", "1 onion"]
    )
    client = build_client(manager, grocery_service)

    response = client.post(
        GROCERY_LIST_PATH,
        json={"recipe_ids": [RECIPE_ONE, RECIPE_ONE, RECIPE_TWO]},
    )

    assert response.status_code == 200
    assert manager.calls == [
        {"recipe_ids": [RECIPE_ONE, RECIPE_TWO], "include_test_data": False}
    ]


def test_create_grocery_list_returns_404_when_any_recipe_is_missing() -> None:
    manager = FakeRecipeManager(ingredients_by_recipe={RECIPE_ONE: ["1 tomato"]})
    grocery_service = FakeGroceryListAggregationService(ingredients=["1 tomato"])
    client = build_client(manager, grocery_service)

    response = client.post(
        GROCERY_LIST_PATH,
        json={"recipe_ids": [RECIPE_ONE, RECIPE_THREE]},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == f"Recipes not found: {RECIPE_THREE}"
    assert grocery_service.calls == []


def test_create_grocery_list_returns_500_when_aggregation_fails() -> None:
    manager = FakeRecipeManager(ingredients_by_recipe={RECIPE_ONE: ["1 tomato"]})
    grocery_service = FakeGroceryListAggregationService(error="llm down")
    client = build_client(manager, grocery_service)

    response = client.post(GROCERY_LIST_PATH, json={"recipe_ids": [RECIPE_ONE]})

    assert response.status_code == 500
    assert response.json()["detail"] == "Error generating grocery list"


def test_create_grocery_list_validates_recipe_ids_payload() -> None:
    manager = FakeRecipeManager()
    grocery_service = FakeGroceryListAggregationService()
    client = build_client(manager, grocery_service)

    response = client.post(GROCERY_LIST_PATH, json={"recipe_ids": []})
    assert response.status_code == 422

    response = client.post(GROCERY_LIST_PATH, json={"recipe_ids": ["not-a-uuid"]})
    assert response.status_code == 422
