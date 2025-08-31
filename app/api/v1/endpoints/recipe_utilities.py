from typing import Union

from fastapi import APIRouter, Body, Depends

from app.core.config import settings
from app.core.dependencies import (
    get_recipe_cleanup_service,
    get_recipe_extractor,
)
from app.core.logging import get_logger
from app.api.schemas import (
    Recipe,
    RecipeCleanupRequest,
    RecipeCleanupResponse,
    RecipeIngestionRequest,
)

router = APIRouter(
    prefix=f"{settings.API_V1_STR}", tags=["Recipe Utilities (Temporary)"]
)
logger = get_logger(__name__)

RECIPE_BODY = Body()
CLEANUP_BODY = Body()

# Dependency instances to satisfy Ruff B008
recipe_extractor_dep = Depends(get_recipe_extractor)
recipe_cleanup_service_dep = Depends(get_recipe_cleanup_service)


@router.post("/ingest-raw")
def ingest_raw_recipe(
    ingestion_input_request: RecipeIngestionRequest = RECIPE_BODY,
    recipe_extractor=recipe_extractor_dep,
) -> Union[Recipe, dict]:
    """
    Extract structured recipe data from raw text input.

    TEMPORARY BUILDING BLOCK: This endpoint will be removed in future versions.
    Use /recipes/process-and-store for the complete end-to-end flow.

    Takes unstructured recipe text and returns a structured Recipe object
    with title, ingredients, instructions, servings, and timing information.
    If extraction fails, returns an error response.
    """
    extracted_recipe, error = recipe_extractor.extract_recipe_from_raw_text(
        ingestion_input_request.raw_input
    )

    if error:
        return {"error": error, "success": False}

    return extracted_recipe


@router.post("/cleanup", response_model=RecipeCleanupResponse)
def recipe_cleanup(
    cleanup_request: RecipeCleanupRequest = CLEANUP_BODY,
    recipe_cleanup_service=recipe_cleanup_service_dep,
) -> RecipeCleanupResponse:
    """
    Clean up messy recipe input data (HTML, scraped content, etc.)
    and return cleaned text suitable for recipe extraction.

    TEMPORARY BUILDING BLOCK: This endpoint will be removed in future versions.
    Use /recipes/process-and-store for the complete end-to-end flow.
    """
    cleaned_text = recipe_cleanup_service.cleanup_input(cleanup_request.raw_text)

    return RecipeCleanupResponse(
        cleaned_text=cleaned_text,
        source_url=cleanup_request.source_url,
        original_length=len(cleanup_request.raw_text),
        cleaned_length=len(cleaned_text),
    )
