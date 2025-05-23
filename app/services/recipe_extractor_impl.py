import logging

from app.core.prompts import RECIPE_EXTRACTION_SYSTEM_PROMPT
from app.schemas.ingest import RecipeIngestionRequest
from app.schemas.recipe import Recipe
from app.services.llm_test_service import make_llm_call_structured_output_generic
from app.services.recipe_extractor import RecipeExtractorService

logger = logging.getLogger(__name__)


class RecipeExtractorImpl(RecipeExtractorService):
    def extract_recipe_from_raw_text(
        self, recipe_ingestion_request: RecipeIngestionRequest
    ) -> Recipe:
        logger.info(
            f"Extracting recipe from text input: {recipe_ingestion_request.raw_input}"
        )
        user_prompt: str = recipe_ingestion_request.raw_input

        extracted_recipe: Recipe = make_llm_call_structured_output_generic(
            user_prompt=user_prompt,
            system_prompt=RECIPE_EXTRACTION_SYSTEM_PROMPT,
            model_class=Recipe,
            schema_name="recipe",
        )
        logger.info(f"Result of extracted recipe: {extracted_recipe}")

        return extracted_recipe
