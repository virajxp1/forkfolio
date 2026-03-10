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
            return self._dedupe_preserve_order(cleaned_ingredients), None

        aggregated = [
            ingredient.strip()
            for ingredient in response.ingredients
            if ingredient and ingredient.strip()
        ]
        if not aggregated:
            return self._dedupe_preserve_order(cleaned_ingredients), None

        merged = self._dedupe_preserve_order(aggregated)
        existing = {self._normalize_ingredient(value) for value in merged}
        for ingredient in cleaned_ingredients:
            normalized = self._normalize_ingredient(ingredient)
            if normalized not in existing:
                merged.append(ingredient)
                existing.add(normalized)

        return merged, None

    @staticmethod
    def _build_user_prompt(ingredients: list[str]) -> str:
        payload = {"ingredients": ingredients}
        return json.dumps(payload, ensure_ascii=True)

    @staticmethod
    def _normalize_ingredient(value: str) -> str:
        return " ".join(value.lower().split())

    @classmethod
    def _dedupe_preserve_order(cls, values: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = cls._normalize_ingredient(value)
            if normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(value)
        return deduped
