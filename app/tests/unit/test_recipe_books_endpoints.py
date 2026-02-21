from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import recipe_books
from app.core.dependencies import get_recipe_book_manager


class StubRecipeBookManager:
    def __init__(self):
        self.create_result = (
            {
                "id": "book-1",
                "name": "Italian Recipes",
                "normalized_name": "italian recipes",
                "recipe_count": 0,
            },
            True,
        )
        self.recipe_book_by_name = {
            "id": "book-1",
            "name": "Italian Recipes",
            "normalized_name": "italian recipes",
            "recipe_ids": ["recipe-1"],
            "recipe_count": 1,
        }
        self.recipe_book_by_id = self.recipe_book_by_name.copy()
        self.list_result = [self.recipe_book_by_name.copy()]
        self.stats_result = {
            "total_recipe_books": 1,
            "total_recipe_book_links": 1,
            "unique_recipes_in_books": 1,
            "avg_recipes_per_book": 1.0,
        }
        self.recipe_exists_result = True
        self.books_for_recipe_result = [self.recipe_book_by_name.copy()]
        self.add_result = {"book_exists": True, "recipe_exists": True, "added": True}
        self.remove_result = {"book_exists": True, "removed": True}

    def create_recipe_book(self, name: str, description: str | None = None):
        return self.create_result

    def get_full_recipe_book_by_name(self, name: str):
        return self.recipe_book_by_name

    def list_recipe_books(self, limit: int = 50):
        return self.list_result

    def get_recipe_book_stats(self):
        return self.stats_result

    def recipe_exists(self, recipe_id: str):
        return self.recipe_exists_result

    def get_recipe_books_for_recipe(self, recipe_id: str):
        return self.books_for_recipe_result

    def get_full_recipe_book_by_id(self, recipe_book_id: str):
        return self.recipe_book_by_id

    def add_recipe_to_book(self, recipe_book_id: str, recipe_id: str):
        return self.add_result

    def remove_recipe_from_book(self, recipe_book_id: str, recipe_id: str):
        return self.remove_result


def build_recipe_books_app(manager: StubRecipeBookManager) -> FastAPI:
    app = FastAPI()
    app.include_router(recipe_books.router)
    app.dependency_overrides[get_recipe_book_manager] = lambda: manager
    return app


def test_create_recipe_book_endpoint_returns_payload() -> None:
    manager = StubRecipeBookManager()
    client = TestClient(build_recipe_books_app(manager))

    response = client.post(
        "/api/v1/recipe-books/",
        json={"name": "Italian Recipes", "description": "Dinner ideas"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["created"] is True
    assert body["recipe_book"]["id"] == "book-1"


def test_get_recipe_books_endpoint_by_name_not_found() -> None:
    manager = StubRecipeBookManager()
    manager.recipe_book_by_name = None
    client = TestClient(build_recipe_books_app(manager))

    response = client.get("/api/v1/recipe-books/", params={"name": "missing"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Recipe book not found"


def test_get_recipe_books_for_recipe_returns_404_when_recipe_missing() -> None:
    manager = StubRecipeBookManager()
    manager.recipe_exists_result = False
    client = TestClient(build_recipe_books_app(manager))

    response = client.get("/api/v1/recipe-books/by-recipe/recipe-1")

    assert response.status_code == 404
    assert response.json()["detail"] == "Recipe not found"


def test_add_recipe_to_book_endpoint_handles_missing_book() -> None:
    manager = StubRecipeBookManager()
    manager.add_result = {"book_exists": False, "recipe_exists": True, "added": False}
    client = TestClient(build_recipe_books_app(manager))

    response = client.put("/api/v1/recipe-books/book-1/recipes/recipe-1")

    assert response.status_code == 404
    assert response.json()["detail"] == "Recipe book not found"


def test_add_recipe_to_book_endpoint_handles_missing_recipe() -> None:
    manager = StubRecipeBookManager()
    manager.add_result = {"book_exists": True, "recipe_exists": False, "added": False}
    client = TestClient(build_recipe_books_app(manager))

    response = client.put("/api/v1/recipe-books/book-1/recipes/recipe-1")

    assert response.status_code == 404
    assert response.json()["detail"] == "Recipe not found"


def test_remove_recipe_from_book_endpoint_returns_removed() -> None:
    manager = StubRecipeBookManager()
    manager.remove_result = {"book_exists": True, "removed": True}
    client = TestClient(build_recipe_books_app(manager))

    response = client.delete("/api/v1/recipe-books/book-1/recipes/recipe-1")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["removed"] is True


def test_get_recipe_book_stats_endpoint_returns_stats() -> None:
    manager = StubRecipeBookManager()
    client = TestClient(build_recipe_books_app(manager))

    response = client.get("/api/v1/recipe-books/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["stats"]["total_recipe_books"] == 1
