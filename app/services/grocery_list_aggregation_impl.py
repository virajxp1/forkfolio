import json
import re
from typing import Optional

from pydantic import BaseModel, Field

from app.core.prompts import GROCERY_LIST_AGGREGATION_SYSTEM_PROMPT
from app.services.grocery_list_aggregation import GroceryListAggregationService
from app.services.llm_generation_service import make_llm_call_structured_output_generic


class GroceryListAggregationResult(BaseModel):
    ingredients: list[str] = Field(default_factory=list)


_INGREDIENT_STOPWORDS = {
    "a",
    "an",
    "and",
    "approximately",
    "as",
    "can",
    "chopped",
    "clove",
    "cup",
    "cups",
    "dash",
    "diced",
    "fresh",
    "for",
    "from",
    "g",
    "garnish",
    "gram",
    "grams",
    "inch",
    "inches",
    "jar",
    "kg",
    "lb",
    "lbs",
    "large",
    "medium",
    "minced",
    "of",
    "optional",
    "or",
    "oz",
    "package",
    "pinch",
    "pound",
    "pounds",
    "small",
    "sliced",
    "taste",
    "tbsp",
    "teaspoon",
    "teaspoons",
    "to",
    "tsp",
    "whole",
    "with",
}


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
        aggregated = self._restore_missing_coverage(cleaned_ingredients, aggregated)
        return aggregated, None

    @staticmethod
    def _build_user_prompt(ingredients: list[str]) -> str:
        payload = {"ingredients": ingredients}
        return json.dumps(payload, ensure_ascii=True)

    @staticmethod
    def _normalize_token(token: str) -> str:
        normalized = token.strip().lower()
        if not normalized or normalized.isdigit():
            return ""
        if len(normalized) > 4 and normalized.endswith("oes"):
            normalized = normalized[:-2]
        elif len(normalized) > 4 and normalized.endswith("ies"):
            normalized = f"{normalized[:-3]}y"
        elif len(normalized) > 3 and normalized.endswith("s") and not normalized.endswith(
            "ss"
        ):
            normalized = normalized[:-1]
        return normalized

    @classmethod
    def _ingredient_tokens(cls, ingredient: str) -> set[str]:
        tokens = {
            cls._normalize_token(token)
            for token in re.split(r"[^a-z0-9]+", ingredient.lower())
        }
        return {
            token
            for token in tokens
            if token and token not in _INGREDIENT_STOPWORDS and not token.isdigit()
        }

    @classmethod
    def _restore_missing_coverage(
        cls,
        source_ingredients: list[str],
        aggregated_ingredients: list[str],
    ) -> list[str]:
        if not source_ingredients or not aggregated_ingredients:
            return aggregated_ingredients

        restored = list(aggregated_ingredients)
        normalized_output = {
            " ".join(ingredient.strip().lower().split())
            for ingredient in aggregated_ingredients
        }
        output_tokens = set().union(
            *(cls._ingredient_tokens(ingredient) for ingredient in aggregated_ingredients)
        )

        for ingredient in source_ingredients:
            normalized_source = " ".join(ingredient.strip().lower().split())
            source_tokens = cls._ingredient_tokens(ingredient)

            if normalized_source in normalized_output:
                continue
            if source_tokens and output_tokens.intersection(source_tokens):
                continue

            restored.append(ingredient)
            normalized_output.add(normalized_source)
            output_tokens.update(source_tokens)

        return restored
