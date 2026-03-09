import logging
import re
from typing import Optional

from app.core.prompts import RECIPE_EXTRACTION_SYSTEM_PROMPT
from app.api.schemas import Recipe
from app.services.llm_generation_service import (
    make_llm_call_structured_output_generic,
)

logger = logging.getLogger(__name__)


TITLE_SECTION_PREFIXES = (
    "ingredients",
    "instructions",
    "directions",
    "method",
    "servings",
    "total time",
    "prep time",
    "cook time",
)


def _normalize_lines(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value and value.strip()]


def _fallback_title(raw_text: str) -> str:
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.lower().removesuffix(":")
        if any(lowered.startswith(prefix) for prefix in TITLE_SECTION_PREFIXES):
            continue
        return stripped
    return ""


def _fallback_instructions(raw_text: str) -> list[str]:
    fallback_steps: list[str] = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        numbered_step = re.match(r"^\d+[.)]\s*(.+)$", stripped)
        if numbered_step:
            step = numbered_step.group(1).strip()
            if step:
                fallback_steps.append(step)

    return fallback_steps


class RecipeExtractorImpl:
    """
    LLM-backed extractor for structured recipe data from raw text input.
    """

    def extract_recipe_from_raw_text(
        self, raw_text: str
    ) -> tuple[Optional[Recipe], Optional[str]]:
        """
        Extract structured recipe data from raw text using LLM.

        Args:
            raw_text: The unstructured recipe text to process

        Returns:
            A tuple of (recipe, error_message). If successful, recipe contains
            the Recipe object and error_message is None. If failed,
            recipe is None and error_message contains the error.
        """
        if not raw_text or not raw_text.strip():
            return None, "Input text is empty or contains only whitespace"

        # Use the LLM to extract structured recipe data
        result, error = make_llm_call_structured_output_generic(
            user_prompt=raw_text,
            system_prompt=RECIPE_EXTRACTION_SYSTEM_PROMPT,
            model_class=Recipe,
            schema_name="recipe_extraction",
        )

        if error or not result:
            return result, error

        title = result.title.strip()
        ingredients = _normalize_lines(result.ingredients)
        instructions = _normalize_lines(result.instructions)
        servings = result.servings.strip()
        total_time = result.total_time.strip()

        if not title:
            title = _fallback_title(raw_text)
        if not instructions:
            instructions = _fallback_instructions(raw_text)

        normalized_recipe = Recipe(
            title=title,
            ingredients=ingredients,
            instructions=instructions,
            servings=servings,
            total_time=total_time,
        )

        return normalized_recipe, None
