import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import recipes
from app.core.config import settings
from app.core.dependencies import (
    get_recipe_embeddings_service,
    get_recipe_manager,
    get_recipe_search_reranker_service,
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
        ingredient_previews: dict[str, list[str]] | None = None,
    ):
        self.results = results or []
        self.error = error
        self.ingredient_previews = ingredient_previews or {}
        self.calls: list[dict] = []
        self.preview_calls: list[dict] = []

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

    def get_ingredient_previews(
        self,
        recipe_ids: list[str],
        max_ingredients: int = 8,
    ) -> dict[str, list[str]]:
        self.preview_calls.append(
            {
                "recipe_ids": recipe_ids,
                "max_ingredients": max_ingredients,
            }
        )
        return {
            recipe_id: self.ingredient_previews.get(recipe_id, [])
            for recipe_id in recipe_ids
        }


class FakeRerankerService:
    def __init__(
        self,
        ranked: list[dict] | None = None,
        error: Exception | None = None,
    ):
        self.ranked = ranked or []
        self.error = error
        self.calls: list[dict] = []

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        max_results: int,
    ) -> list[dict]:
        self.calls.append(
            {
                "query": query,
                "candidates": candidates,
                "max_results": max_results,
            }
        )
        if self.error:
            raise self.error
        return self.ranked


def build_client(
    recipe_manager: FakeRecipeManager,
    embeddings_service: FakeEmbeddingsService,
    reranker_service: FakeRerankerService | None = None,
) -> TestClient:
    app = FastAPI()
    app.include_router(recipes.router)
    app.dependency_overrides[get_recipe_manager] = lambda: recipe_manager
    app.dependency_overrides[get_recipe_embeddings_service] = lambda: embeddings_service
    if reranker_service is not None:
        app.dependency_overrides[get_recipe_search_reranker_service] = lambda: (
            reranker_service
        )
    return TestClient(app)


SEMANTIC_SEARCH_PATH = f"{settings.API_BASE_PATH}/recipes/search/semantic"


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
        SEMANTIC_SEARCH_PATH,
        params={"query": "lasagna", "limit": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["query"] == "lasagna"
    assert payload["count"] == 1
    assert payload["results"] == expected_results

    assert fake_embeddings.calls == ["lasagna"]
    expected_limit = 5
    if settings.SEMANTIC_SEARCH_RERANK_ENABLED:
        expected_limit = max(5, settings.SEMANTIC_SEARCH_RERANK_CANDIDATE_COUNT)
    assert fake_manager.calls == [
        {
            "embedding": [0.4, 0.5, 0.6],
            "embedding_type": "title_ingredients",
            "limit": expected_limit,
            "max_distance": settings.SEMANTIC_SEARCH_MAX_DISTANCE,
        }
    ]


def test_semantic_search_validates_query_length() -> None:
    fake_manager = FakeRecipeManager()
    fake_embeddings = FakeEmbeddingsService()
    client = build_client(fake_manager, fake_embeddings)

    response = client.get(
        SEMANTIC_SEARCH_PATH,
        params={"query": "a"},
    )

    assert response.status_code == 422


def test_semantic_search_rejects_whitespace_only_query() -> None:
    fake_manager = FakeRecipeManager()
    fake_embeddings = FakeEmbeddingsService()
    client = build_client(fake_manager, fake_embeddings)

    response = client.get(
        SEMANTIC_SEARCH_PATH,
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
        SEMANTIC_SEARCH_PATH,
        params={"query": "lasagna"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Error performing semantic search: embeddings down"
    )


def test_semantic_search_strips_wrapping_quotes() -> None:
    expected_results = [
        {
            "id": "recipe-1",
            "name": "Classic Lasagne",
            "distance": 0.08,
        }
    ]
    fake_manager = FakeRecipeManager(results=expected_results)
    fake_embeddings = FakeEmbeddingsService()
    client = build_client(fake_manager, fake_embeddings)

    response = client.get(
        SEMANTIC_SEARCH_PATH,
        params={"query": '"lasagna"'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "lasagna"
    assert fake_embeddings.calls == ["lasagna"]


def test_semantic_search_applies_rerank_when_enabled(monkeypatch) -> None:
    recipe_one = str(uuid.uuid4())
    recipe_two = str(uuid.uuid4())
    expected_results = [
        {
            "id": uuid.UUID(recipe_one),
            "name": "Herby Pasta",
            "distance": 0.09,
        },
        {
            "id": uuid.UUID(recipe_two),
            "name": "Carbonara",
            "distance": 0.11,
        },
    ]
    ingredient_previews = {
        recipe_one: ["pasta", "herbs"],
        recipe_two: ["spaghetti", "egg", "pecorino"],
    }
    fake_manager = FakeRecipeManager(
        results=expected_results, ingredient_previews=ingredient_previews
    )
    fake_embeddings = FakeEmbeddingsService(embedding=[0.4, 0.5, 0.6])
    fake_reranker = FakeRerankerService(
        ranked=[
            {"id": recipe_two, "score": 0.97},
            {"id": recipe_one, "score": 0.76},
        ]
    )
    client = build_client(fake_manager, fake_embeddings, fake_reranker)

    original_enabled = settings.SEMANTIC_SEARCH_RERANK_ENABLED
    original_candidate_count = settings.SEMANTIC_SEARCH_RERANK_CANDIDATE_COUNT
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_RERANK_ENABLED", True)
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_RERANK_CANDIDATE_COUNT", 5)
    try:
        response = client.get(
            SEMANTIC_SEARCH_PATH,
            params={"query": "pasta", "limit": 2},
        )
    finally:
        monkeypatch.setattr(
            settings, "SEMANTIC_SEARCH_RERANK_ENABLED", original_enabled
        )
        monkeypatch.setattr(
            settings,
            "SEMANTIC_SEARCH_RERANK_CANDIDATE_COUNT",
            original_candidate_count,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"][0]["id"] == recipe_two
    assert payload["results"][1]["id"] == recipe_one
    assert payload["results"][0]["rerank_score"] == 0.97
    assert payload["results"][1]["rerank_score"] == 0.76
    assert len(fake_reranker.calls) == 1
    assert fake_manager.preview_calls == [
        {"recipe_ids": [recipe_one, recipe_two], "max_ingredients": 8}
    ]


def test_semantic_search_falls_back_when_reranker_returns_unknown_ids(
    monkeypatch,
) -> None:
    expected_results = [
        {"id": str(uuid.uuid4()), "name": "Herby Pasta", "distance": 0.09},
        {"id": str(uuid.uuid4()), "name": "Carbonara", "distance": 0.11},
    ]
    fake_manager = FakeRecipeManager(results=expected_results)
    fake_embeddings = FakeEmbeddingsService()
    fake_reranker = FakeRerankerService(
        ranked=[{"id": str(uuid.uuid4()), "score": 0.99}]
    )
    client = build_client(fake_manager, fake_embeddings, fake_reranker)

    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_RERANK_ENABLED", True)
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_RERANK_CANDIDATE_COUNT", 5)

    response = client.get(
        SEMANTIC_SEARCH_PATH,
        params={"query": "pasta", "limit": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"][0]["id"] == expected_results[0]["id"]
    assert payload["results"][1]["id"] == expected_results[1]["id"]
    assert "rerank_score" not in payload["results"][0]
    assert "rerank_score" not in payload["results"][1]


def test_semantic_search_falls_back_when_reranker_raises(monkeypatch) -> None:
    expected_results = [
        {"id": str(uuid.uuid4()), "name": "Herby Pasta", "distance": 0.09},
        {"id": str(uuid.uuid4()), "name": "Carbonara", "distance": 0.11},
    ]
    fake_manager = FakeRecipeManager(results=expected_results)
    fake_embeddings = FakeEmbeddingsService()
    fake_reranker = FakeRerankerService(error=RuntimeError("rerank down"))
    client = build_client(fake_manager, fake_embeddings, fake_reranker)

    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_RERANK_ENABLED", True)
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_RERANK_CANDIDATE_COUNT", 5)

    response = client.get(
        SEMANTIC_SEARCH_PATH,
        params={"query": "pasta", "limit": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"][0]["id"] == expected_results[0]["id"]
    assert payload["results"][1]["id"] == expected_results[1]["id"]


def test_semantic_search_filters_low_rerank_scores(monkeypatch) -> None:
    recipe_one = str(uuid.uuid4())
    recipe_two = str(uuid.uuid4())
    expected_results = [
        {"id": recipe_one, "name": "Simple Pasta", "distance": 0.10},
        {"id": recipe_two, "name": "Thai Green Curry", "distance": 0.12},
    ]
    fake_manager = FakeRecipeManager(results=expected_results)
    fake_embeddings = FakeEmbeddingsService()
    fake_reranker = FakeRerankerService(
        ranked=[
            {"id": recipe_one, "score": 0.72},
            {"id": recipe_two, "score": 0.22},
        ]
    )
    client = build_client(fake_manager, fake_embeddings, fake_reranker)

    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_RERANK_ENABLED", True)
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_RERANK_CANDIDATE_COUNT", 5)
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_RERANK_MIN_SCORE", 0.40)
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_RERANK_WEIGHT", 0.70)

    response = client.get(
        SEMANTIC_SEARCH_PATH,
        params={"query": "lasagna", "limit": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["id"] == recipe_one
    assert payload["results"][0]["rerank_score"] == 0.72
    assert "combined_score" in payload["results"][0]


def test_semantic_search_uses_fallback_boost_when_strict_is_empty(monkeypatch) -> None:
    recipe_one = str(uuid.uuid4())
    recipe_two = str(uuid.uuid4())
    expected_results = [
        {"id": recipe_one, "name": "Indian Chana Masala", "distance": 0.16},
        {"id": recipe_two, "name": "Indian Aloo Gobi", "distance": 0.19},
    ]
    fake_manager = FakeRecipeManager(results=expected_results)
    fake_embeddings = FakeEmbeddingsService()
    fake_reranker = FakeRerankerService(
        ranked=[
            {"id": recipe_one, "score": 0.25},
            {"id": recipe_two, "score": 0.15},
        ]
    )
    client = build_client(fake_manager, fake_embeddings, fake_reranker)

    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_RERANK_ENABLED", True)
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_RERANK_CANDIDATE_COUNT", 5)
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_RERANK_MIN_SCORE", 0.40)
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_RERANK_FALLBACK_MIN_SCORE", 0.25)
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_RERANK_WEIGHT", 0.70)
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_RERANK_CUISINE_BOOST", 0.15)
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_RERANK_FAMILY_BOOST", 0.10)

    response = client.get(
        SEMANTIC_SEARCH_PATH,
        params={"query": "paneer tikka masala", "limit": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert payload["results"][0]["id"] == recipe_one
    assert payload["results"][1]["id"] == recipe_two
    assert payload["results"][0]["rerank_mode"] == "fallback"
    assert payload["results"][1]["rerank_mode"] == "fallback"
    assert payload["results"][0]["rerank_score"] == 0.5
    assert payload["results"][0]["raw_rerank_score"] == 0.25
