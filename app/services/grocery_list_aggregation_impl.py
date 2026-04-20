import json
from typing import Optional

from pydantic import BaseModel, Field

from app.core.prompts import GROCERY_LIST_AGGREGATION_SYSTEM_PROMPT
from app.services.grocery_list_aggregation import GroceryListAggregationService
from app.services.llm_generation_service import make_llm_call_structured_output_generic


class GroceryListAggregationResult(BaseModel):
    ingredients: list[str] = Field(default_factory=list)


class GroceryListAggregationServiceImpl(GroceryListAggregationService):
    """LLM-backed service that merges recipe ingredients into one grocery list."""

    def aggregate_ingredients(
        self,
        ingredients: list[str],
    ) -> tuple[Optional[list[str]], Optional[str]]:
        cleaned_ingredients = [
            ingredient.strip()
            for ingredient in ingredients
            if ingredient is not None and ingredient.strip()
        ]
        if not cleaned_ingredients:
            return [], None

        response, error = make_llm_call_structured_output_generic(
            user_prompt=self._build_user_prompt(cleaned_ingredients),
            system_prompt=GROCERY_LIST_AGGREGATION_SYSTEM_PROMPT,
            model_class=GroceryListAggregationResult,
            schema_name="grocery_list_aggregation",
        )
        if error or not response:
            return None, error or "Failed to aggregate grocery ingredients"

        aggregated = [
            ingredient.strip()
            for ingredient in response.ingredients
            if ingredient and ingredient.strip()
        ]
        if not aggregated:
            # Fall back to the original cleaned list if the LLM returns an empty
            # aggregation. An empty grocery list is worse UX than preserving the
            # source ingredients.
            return cleaned_ingredients, None
        return aggregated, None

    @staticmethod
    def _build_user_prompt(ingredients: list[str]) -> str:
        payload = {"ingredients": ingredients}
        return json.dumps(payload, ensure_ascii=True)
