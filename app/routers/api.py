from typing import Union

from fastapi import APIRouter, Body, Depends, HTTPException

from app.core.config import settings
from app.core.dependencies import (
    get_recipe_cleanup_service,
    get_recipe_extractor,
)
from app.schemas.ingest import RecipeIngestionRequest
from app.schemas.recipe import Recipe, RecipeCleanupRequest, RecipeCleanupResponse
from app.services.data.managers.recipe_manager import RecipeManager
from app.services.recipe_extractor_impl import RecipeExtractorImpl
from app.services.recipe_input_cleanup_impl import RecipeInputCleanupServiceImpl
from app.services.recipe_processing_service import RecipeProcessingService

router = APIRouter(prefix=settings.API_V1_STR)

RECIPE_BODY = Body()
CLEANUP_BODY = Body()

# Dependency instances to satisfy Ruff B008
recipe_extractor_dep = Depends(get_recipe_extractor)
recipe_cleanup_service_dep = Depends(get_recipe_cleanup_service)


@router.get("/")
def root():
    return {"message": "Welcome to ForkFolio API"}


@router.post("/ingest-raw-recipe")
def ingest_raw_recipe(
    ingestion_input_request: RecipeIngestionRequest = RECIPE_BODY,
    recipe_extractor: RecipeExtractorImpl = recipe_extractor_dep,
) -> Union[Recipe, dict]:
    """
    Extract structured recipe data from raw text input.

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


@router.post("/cleanup-raw-recipe", response_model=RecipeCleanupResponse)
def recipe_cleanup(
    cleanup_request: RecipeCleanupRequest = CLEANUP_BODY,
    recipe_cleanup_service: RecipeInputCleanupServiceImpl = recipe_cleanup_service_dep,
) -> RecipeCleanupResponse:
    """
    Clean up messy recipe input data (HTML, scraped content, etc.)
    and return cleaned text suitable for recipe extraction.
    """
    cleaned_text = recipe_cleanup_service.cleanup_input(cleanup_request.raw_text)

    return RecipeCleanupResponse(
        cleaned_text=cleaned_text,
        source_url=cleanup_request.source_url,
        original_length=len(cleanup_request.raw_text),
        cleaned_length=len(cleaned_text),
    )


@router.post("/process-and-store-recipe")
def process_and_store_recipe(
    ingestion_request: RecipeIngestionRequest = RECIPE_BODY,
) -> dict:
    """
    Complete recipe processing pipeline:
    1. Cleanup raw input
    2. Extract structured recipe data
    3. Store in database
    4. Return database ID

    Takes raw unstructured recipe text and returns the database ID
    of the stored recipe, or an error if processing fails.
    """
    processing_service = RecipeProcessingService()

    recipe_id, error = processing_service.process_raw_recipe(
        raw_input=ingestion_request.raw_input,
        source_url=None,  # Could extend request model to include source_url if needed
    )

    if error:
        return {"error": error, "success": False}

    return {
        "recipe_id": recipe_id,
        "success": True,
        "message": "Recipe processed and stored successfully",
    }


@router.get("/recipe/{recipe_id}")
def get_recipe(recipe_id: str) -> dict:
    """
    Get a complete recipe by its UUID.

    Returns the recipe with all ingredients and instructions,
    or 404 if the recipe is not found.
    """
    recipe_manager = RecipeManager()

    try:
        recipe_data = recipe_manager.get_full_recipe(recipe_id)

        if not recipe_data:
            raise HTTPException(status_code=404, detail="Recipe not found")

        return {"recipe": recipe_data, "success": True}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving recipe: {e!s}"
        ) from e
    finally:
        recipe_manager.close()
