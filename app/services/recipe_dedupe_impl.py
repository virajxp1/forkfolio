from typing import Optional

from pydantic import BaseModel, Field

from app.api.schemas import Recipe
from app.core.config import settings
from app.core.logging import get_logger
from app.core.prompts import DEDUPLICATION_SYSTEM_PROMPT
from app.services.data.managers.recipe_manager import RecipeManager
from app.services.llm_generation_service import (
    make_embedding,
    make_llm_call_structured_output_generic,
)
from app.services.recipe_embeddings_impl import RecipeEmbeddingsServiceImpl

logger = get_logger(__name__)


def _get_dedupe_settings() -> tuple[float, float, str]:
    return (
        settings.DEDUPE_DISTANCE_THRESHOLD,
        settings.DEDUPE_STRICT_DUPLICATE_DISTANCE_THRESHOLD,
        settings.DEDUPE_EMBEDDING_TYPE,
    )


class DedupeDecision(BaseModel):
    decision: str = Field(..., pattern="^(duplicate|distinct)$")
    reason: str = ""


class RecipeDedupeServiceImpl:
    """Deduplicate recipes using embeddings + LLM adjudication."""

    def __init__(self, recipe_manager: RecipeManager | None = None):
        self.recipe_manager = recipe_manager or RecipeManager()
        (
            self.distance_threshold,
            self.strict_duplicate_threshold,
            self.embedding_type,
        ) = _get_dedupe_settings()

    def find_duplicate(
        self, recipe: Recipe
    ) -> tuple[bool, Optional[str], Optional[list[float]]]:
        embedding_text = RecipeEmbeddingsServiceImpl._build_title_ingredients_text(
            recipe.title, recipe.ingredients
        )
        embedding = make_embedding(embedding_text)
        nearest = self.recipe_manager.find_nearest_embedding(
            embedding=embedding,
            embedding_type=self.embedding_type,
        )
        if not nearest:
            return False, None, embedding

        distance = nearest["distance"]
        if distance is None:
            return False, None, embedding

        if distance <= self.strict_duplicate_threshold:
            return True, nearest["recipe_id"], embedding

        if distance > self.distance_threshold:
            return False, None, embedding

        existing_recipe = self.recipe_manager.get_full_recipe(nearest["recipe_id"])
        if not existing_recipe:
            return False, None, embedding

        decision, error = make_llm_call_structured_output_generic(
            user_prompt=self._build_user_prompt(recipe, existing_recipe),
            system_prompt=DEDUPLICATION_SYSTEM_PROMPT,
            model_class=DedupeDecision,
            schema_name="dedupe_decision",
        )
        if error or not decision:
            logger.warning(f"Dedupe LLM failed; allowing insert. Error: {error}")
            return False, None, embedding

        if decision.decision == "duplicate":
            return True, nearest["recipe_id"], embedding

        return False, None, embedding

    @staticmethod
    def _build_user_prompt(recipe: Recipe, existing_recipe: dict) -> str:
        def format_recipe(
            title: str, ingredients: list[str], instructions: list[str]
        ) -> str:
            ingredients_text = "\n".join(f"- {item}" for item in ingredients)
            instructions_text = "\n".join(
                f"{idx + 1}. {item}" for idx, item in enumerate(instructions)
            )
            return (
                f"Title: {title}\n"
                f"Ingredients:\n{ingredients_text}\n\n"
                f"Instructions:\n{instructions_text}"
            )

        new_recipe_text = format_recipe(
            recipe.title, recipe.ingredients, recipe.instructions
        )
        existing_recipe_text = format_recipe(
            existing_recipe.get("title", ""),
            existing_recipe.get("ingredients", []),
            existing_recipe.get("instructions", []),
        )

        return (
            "Compare the NEW recipe with the EXISTING recipe. "
            "Decide if they are essentially the same dish with only minor variations.\n\n"
            "NEW RECIPE:\n"
            f"{new_recipe_text}\n\n"
            "EXISTING RECIPE:\n"
            f"{existing_recipe_text}"
        )
