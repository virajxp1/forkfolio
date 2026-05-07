import json

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.core.prompts import SEARCH_RERANK_SYSTEM_PROMPT
from app.services.llm_generation_service import make_llm_call_structured_output_generic
from app.services.recipe_search_reranker import RecipeSearchRerankerService

logger = get_logger(__name__)


class RankedCandidate(BaseModel):
    id: str
    score: float = Field(..., ge=0.0, le=1.0)


class RerankResponse(BaseModel):
    ranked: list[RankedCandidate]


class RecipeSearchRerankerServiceImpl(RecipeSearchRerankerService):
    """LLM-powered reranker for semantic search candidates."""

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        max_results: int,
    ) -> list[dict]:
        normalized_query = query.strip()
        if not normalized_query:
            return []
        if not candidates:
            return []

        prompt = self._build_user_prompt(normalized_query, candidates, max_results)
        response, error = make_llm_call_structured_output_generic(
            user_prompt=prompt,
            system_prompt=SEARCH_RERANK_SYSTEM_PROMPT,
            model_class=RerankResponse,
            schema_name="recipe_search_rerank",
        )
        if error or not response:
            logger.warning(
                "Rerank failed; falling back to embedding order. Error: %s", error
            )
            return []

        return [{"id": item.id, "score": item.score} for item in response.ranked]

    @staticmethod
    def _to_json_distance(distance_value: object) -> float | None:
        if distance_value is None:
            return None
        try:
            return float(distance_value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _build_user_prompt(query: str, candidates: list[dict], max_results: int) -> str:
        serialized_candidates = []
        for item in candidates:
            candidate_id = item.get("id")
            if candidate_id is None:
                continue
            serialized_candidates.append(
                {
                    "id": str(candidate_id),
                    "title": item.get("name"),
                    "distance": RecipeSearchRerankerServiceImpl._to_json_distance(
                        item.get("distance")
                    ),
                    "ingredients_preview": item.get("ingredients_preview", []),
                }
            )

        payload = {
            "query": query,
            "max_results": max_results,
            "candidates": serialized_candidates,
        }
        return json.dumps(payload, ensure_ascii=True)
