from __future__ import annotations

from typing import Optional

from app.core.config import settings
from app.services.data.managers.recipe_manager import RecipeManager


class RecipeHybridSearchServiceImpl:
    """Run Postgres-native hybrid recipe search."""

    def __init__(self, recipe_manager: RecipeManager | None = None) -> None:
        self.recipe_manager = recipe_manager or RecipeManager()

    def search(
        self,
        query: str,
        query_embedding: list[float],
        limit: int = 10,
        *,
        weights: tuple[float, float, float] | None = None,
        include_test_data: bool = False,
        viewer_user_id: Optional[str] = None,
    ) -> list[dict]:
        fts_weight, trigram_weight, vector_weight = (
            weights if weights is not None else self.normalized_weights()
        )
        return self.recipe_manager.search_recipes_hybrid(
            query=query,
            embedding=query_embedding,
            embedding_type="title_ingredients",
            limit=limit,
            include_test_data=include_test_data,
            viewer_user_id=viewer_user_id,
            max_distance=settings.SEMANTIC_SEARCH_V2_MAX_DISTANCE,
            trigram_threshold=settings.SEMANTIC_SEARCH_V2_TRIGRAM_THRESHOLD,
            min_score=settings.SEMANTIC_SEARCH_V2_MIN_SCORE,
            fts_weight=fts_weight,
            trigram_weight=trigram_weight,
            vector_weight=vector_weight,
        )

    @staticmethod
    def normalized_weights() -> tuple[float, float, float]:
        fts_w = max(settings.SEMANTIC_SEARCH_V2_FTS_WEIGHT, 0.0)
        trigram_w = max(settings.SEMANTIC_SEARCH_V2_TRIGRAM_WEIGHT, 0.0)
        vector_w = max(settings.SEMANTIC_SEARCH_V2_VECTOR_WEIGHT, 0.0)
        total = fts_w + trigram_w + vector_w
        if total <= 0.0:
            return (0.45, 0.2, 0.35)
        return (fts_w / total, trigram_w / total, vector_w / total)
