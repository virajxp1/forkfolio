from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import recipes
from app.core.config import settings
from app.core.dependencies import (
    get_recipe_embeddings_service,
    get_recipe_manager,
)


class FakeEmbeddingsService:
    def __init__(
        self,
        embedding: list[float] | None = None,
        error: Exception | None = None,
    ):
        self.embedding = embedding or [0.1, 0.2, 0.3]
        self.error = error
        self.calls: list[str] = []

    def embed_search_query(self, query: str) -> list[float]:
        self.calls.append(query)
        if self.error:
            raise self.error
        return self.embedding


class FakeRecipeManager:
    def __init__(
        self,
        results: list[dict] | None = None,
        error: Exception | None = None,
    ):
        self.results = results or []
        self.error = error
        self.calls: list[dict] = []

    def search_recipes_by_embedding(
        self,
        embedding: list[float],
        embedding_type: str,
        limit: int = 10,
        max_distance: float = 0.35,
    ) -> list[dict]:
        self.calls.append(
            {
                "embedding": embedding,
                "embedding_type": embedding_type,
                "limit": limit,
                "max_distance": max_distance,
            }
        )
        if self.error:
            raise self.error
        return self.results


def build_client(
    recipe_manager: FakeRecipeManager,
    embeddings_service: FakeEmbeddingsService,
) -> TestClient:
    app = FastAPI()
    app.include_router(recipes.router)
    app.dependency_overrides[get_recipe_manager] = lambda: recipe_manager
    app.dependency_overrides[get_recipe_embeddings_service] = lambda: embeddings_service
    return TestClient(app)


def test_semantic_search_returns_results() -> None:
    expected_results = [
        {
            "id": "recipe-1",
            "name": "Classic Lasagne",
            "distance": 0.08,
        }
    ]
    fake_manager = FakeRecipeManager(results=expected_results)
    fake_embeddings = FakeEmbeddingsService(embedding=[0.4, 0.5, 0.6])
    client = build_client(fake_manager, fake_embeddings)

    response = client.get(
        "/api/v1/recipes/search/semantic",
        params={"query": "lasagna", "limit": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["query"] == "lasagna"
    assert payload["count"] == 1
    assert payload["results"] == expected_results

    assert fake_embeddings.calls == ["lasagna"]
    assert fake_manager.calls == [
        {
            "embedding": [0.4, 0.5, 0.6],
            "embedding_type": "title_ingredients",
            "limit": 5,
            "max_distance": settings.SEMANTIC_SEARCH_MAX_DISTANCE,
        }
    ]


def test_semantic_search_validates_query_length() -> None:
    fake_manager = FakeRecipeManager()
    fake_embeddings = FakeEmbeddingsService()
    client = build_client(fake_manager, fake_embeddings)

    response = client.get(
        "/api/v1/recipes/search/semantic",
        params={"query": "a"},
    )

    assert response.status_code == 422


def test_semantic_search_rejects_whitespace_only_query() -> None:
    fake_manager = FakeRecipeManager()
    fake_embeddings = FakeEmbeddingsService()
    client = build_client(fake_manager, fake_embeddings)

    response = client.get(
        "/api/v1/recipes/search/semantic",
        params={"query": "   "},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Query must contain at least 2 non-whitespace characters."
    )
    assert fake_embeddings.calls == []
    assert fake_manager.calls == []


def test_semantic_search_returns_500_on_embedding_error() -> None:
    fake_manager = FakeRecipeManager()
    fake_embeddings = FakeEmbeddingsService(error=RuntimeError("embeddings down"))
    client = build_client(fake_manager, fake_embeddings)

    response = client.get(
        "/api/v1/recipes/search/semantic",
        params={"query": "lasagna"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Error performing semantic search: embeddings down"
    )
