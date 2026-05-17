from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import recipes
from app.core.cache import TTLCache
from app.core.config import settings
from app.core.dependencies import (
    get_recipe_embeddings_service,
    get_recipe_hybrid_search_service,
)
from app.services.recipe_hybrid_search_impl import RecipeHybridSearchServiceImpl


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


class FakeHybridSearchService:
    def __init__(
        self,
        results: list[dict] | None = None,
        error: Exception | None = None,
    ):
        self.results = results or []
        self.error = error
        self.calls: list[dict] = []

    def search(
        self,
        query: str,
        query_embedding: list[float],
        limit: int = 10,
        *,
        weights: tuple[float, float, float] | None = None,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> list[dict]:
        self.calls.append(
            {
                "query": query,
                "query_embedding": query_embedding,
                "limit": limit,
                "weights": weights,
                "include_test_data": include_test_data,
                "viewer_user_id": viewer_user_id,
            }
        )
        if self.error:
            raise self.error
        return self.results

    def normalized_weights(self) -> tuple[float, float, float]:
        return RecipeHybridSearchServiceImpl.normalized_weights()


def build_client(
    *,
    search_service: FakeHybridSearchService | None = None,
    embeddings_service: FakeEmbeddingsService | None = None,
) -> TestClient:
    recipes.hybrid_search_cache.clear()
    app = FastAPI()
    app.include_router(recipes.router)
    if embeddings_service is not None:
        app.dependency_overrides[get_recipe_embeddings_service] = lambda: (
            embeddings_service
        )
    if search_service is not None:
        app.dependency_overrides[get_recipe_hybrid_search_service] = lambda: (
            search_service
        )
    return TestClient(app)


SEARCH_PATH = f"{settings.API_BASE_PATH}/recipes/search/semantic"


def test_semantic_search_returns_results() -> None:
    expected = [
        {
            "id": "recipe-1",
            "name": "Classic Lasagne",
            "distance": 0.08,
            "combined_score": 0.92,
        }
    ]
    fake_search = FakeHybridSearchService(results=expected)
    fake_embeddings = FakeEmbeddingsService(embedding=[0.4, 0.5, 0.6])
    client = build_client(
        search_service=fake_search, embeddings_service=fake_embeddings
    )

    response = client.get(SEARCH_PATH, params={"query": "lasagna", "limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["query"] == "lasagna"
    assert payload["count"] == 1
    assert payload["results"] == expected

    assert fake_embeddings.calls == ["lasagna"]
    assert fake_search.calls == [
        {
            "query": "lasagna",
            "query_embedding": [0.4, 0.5, 0.6],
            "limit": 5,
            "weights": RecipeHybridSearchServiceImpl.normalized_weights(),
            "include_test_data": False,
            "viewer_user_id": None,
        }
    ]


def test_semantic_search_reuses_cached_response(monkeypatch) -> None:
    fake_search = FakeHybridSearchService(
        results=[{"id": "r-1", "name": "Lasagne", "distance": 0.08}]
    )
    fake_embeddings = FakeEmbeddingsService(embedding=[0.4, 0.5, 0.6])
    monkeypatch.setattr(
        recipes,
        "hybrid_search_cache",
        TTLCache[dict](ttl_seconds=300, max_items=32),
    )
    client = build_client(
        search_service=fake_search, embeddings_service=fake_embeddings
    )

    first = client.get(SEARCH_PATH, params={"query": "lasagna", "limit": 5})
    second = client.get(SEARCH_PATH, params={"query": "lasagna", "limit": 5})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()
    assert fake_embeddings.calls == ["lasagna"]
    assert len(fake_search.calls) == 1


def test_semantic_search_cache_key_uses_normalized_weights(monkeypatch) -> None:
    fake_search = FakeHybridSearchService(
        results=[{"id": "r-1", "name": "Lasagne", "distance": 0.08}]
    )
    fake_embeddings = FakeEmbeddingsService(embedding=[0.4, 0.5, 0.6])
    monkeypatch.setattr(
        recipes,
        "hybrid_search_cache",
        TTLCache[dict](ttl_seconds=300, max_items=32),
    )
    client = build_client(
        search_service=fake_search, embeddings_service=fake_embeddings
    )

    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_V2_FTS_WEIGHT", 0.0)
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_V2_TRIGRAM_WEIGHT", 0.0)
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_V2_VECTOR_WEIGHT", 0.0)
    first = client.get(SEARCH_PATH, params={"query": "lasagna", "limit": 5})

    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_V2_FTS_WEIGHT", 0.45)
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_V2_TRIGRAM_WEIGHT", 0.2)
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_V2_VECTOR_WEIGHT", 0.35)
    second = client.get(SEARCH_PATH, params={"query": "lasagna", "limit": 5})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()
    assert fake_embeddings.calls == ["lasagna"]
    assert len(fake_search.calls) == 1
    assert fake_search.calls[0]["weights"] == (0.45, 0.2, 0.35)


def test_semantic_search_cache_is_scoped_by_viewer() -> None:
    fake_search = FakeHybridSearchService(
        results=[{"id": "r-1", "name": "Lasagne", "distance": 0.08}]
    )
    fake_embeddings = FakeEmbeddingsService(embedding=[0.4, 0.5, 0.6])
    client = build_client(
        search_service=fake_search, embeddings_service=fake_embeddings
    )

    public = client.get(SEARCH_PATH, params={"query": "lasagna", "limit": 5})
    viewer = client.get(
        SEARCH_PATH,
        params={"query": "lasagna", "limit": 5},
        headers={"X-Viewer-User-Id": "44444444-4444-4444-4444-444444444444"},
    )

    assert public.status_code == 200
    assert viewer.status_code == 200
    assert fake_embeddings.calls == ["lasagna", "lasagna"]
    assert fake_search.calls[0]["viewer_user_id"] is None
    assert fake_search.calls[0]["weights"] == (
        RecipeHybridSearchServiceImpl.normalized_weights()
    )
    assert (
        fake_search.calls[1]["viewer_user_id"] == "44444444-4444-4444-4444-444444444444"
    )


def test_semantic_search_validates_query_length() -> None:
    fake_search = FakeHybridSearchService()
    fake_embeddings = FakeEmbeddingsService()
    client = build_client(
        search_service=fake_search, embeddings_service=fake_embeddings
    )

    response = client.get(SEARCH_PATH, params={"query": "a"})

    assert response.status_code == 422


def test_semantic_search_rejects_whitespace_only_query() -> None:
    fake_search = FakeHybridSearchService()
    fake_embeddings = FakeEmbeddingsService()
    client = build_client(
        search_service=fake_search, embeddings_service=fake_embeddings
    )

    response = client.get(SEARCH_PATH, params={"query": "   "})

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Query must contain at least 2 non-whitespace characters."
    )
    assert fake_embeddings.calls == []
    assert fake_search.calls == []


def test_semantic_search_returns_500_on_embedding_error() -> None:
    fake_search = FakeHybridSearchService()
    fake_embeddings = FakeEmbeddingsService(error=RuntimeError("embeddings down"))
    client = build_client(
        search_service=fake_search, embeddings_service=fake_embeddings
    )

    response = client.get(SEARCH_PATH, params={"query": "lasagna"})

    assert response.status_code == 500
    assert (
        response.json()["detail"] == "Error performing hybrid search: embeddings down"
    )


def test_semantic_search_returns_500_on_search_error() -> None:
    fake_search = FakeHybridSearchService(error=RuntimeError("search down"))
    fake_embeddings = FakeEmbeddingsService()
    client = build_client(
        search_service=fake_search, embeddings_service=fake_embeddings
    )

    response = client.get(SEARCH_PATH, params={"query": "lasagna"})

    assert response.status_code == 500
    assert response.json()["detail"] == "Error performing hybrid search: search down"


def test_semantic_search_strips_wrapping_quotes() -> None:
    fake_search = FakeHybridSearchService(
        results=[{"id": "r-1", "name": "Lasagne", "distance": 0.08}]
    )
    fake_embeddings = FakeEmbeddingsService()
    client = build_client(
        search_service=fake_search, embeddings_service=fake_embeddings
    )

    response = client.get(SEARCH_PATH, params={"query": '"lasagna"'})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "lasagna"
    assert fake_embeddings.calls == ["lasagna"]
    assert fake_search.calls[0]["query"] == "lasagna"
