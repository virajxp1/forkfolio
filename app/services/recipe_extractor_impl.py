import logging
from typing import Optional

from app.core.prompts import RECIPE_EXTRACTION_SYSTEM_PROMPT
from app.schemas.recipe import Recipe
from app.services.llm_generation_service import (
    make_llm_call_structured_output_generic,
)
from app.services.recipe_extractor import RecipeExtractorService

logger = logging.getLogger(__name__)


class RecipeExtractorImpl(RecipeExtractorService):
    """
    Implementation of RecipeExtractorService that uses LLM to extract recipe data
    from raw text input.
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

        return result, error
