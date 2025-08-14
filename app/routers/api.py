from typing import Union

from fastapi import APIRouter, Body, Depends, HTTPException

from app.core.config import settings
from app.core.dependencies import (
    get_recipe_cleanup_service,
    get_recipe_extractor,
    get_recipe_manager,
    get_recipe_processing_service,
)
from app.core.logging import get_logger
from app.api.schemas import RecipeIngestionRequest
from app.api.schemas import Recipe, RecipeCleanupRequest, RecipeCleanupResponse
from app.services.data.supabase_client import get_db_context, get_pool_status

router = APIRouter(prefix=settings.API_V1_STR)
logger = get_logger(__name__)

RECIPE_BODY = Body()
CLEANUP_BODY = Body()

# Dependency instances to satisfy Ruff B008
recipe_extractor_dep = Depends(get_recipe_extractor)
recipe_cleanup_service_dep = Depends(get_recipe_cleanup_service)
recipe_manager_dep = Depends(get_recipe_manager)
recipe_processing_service_dep = Depends(get_recipe_processing_service)


@router.get("/")
def root():
    return {"message": "Welcome to ForkFolio API"}


@router.post("/ingest-raw-recipe")
def ingest_raw_recipe(
    ingestion_input_request: RecipeIngestionRequest = RECIPE_BODY,
    recipe_extractor=recipe_extractor_dep,
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
    recipe_cleanup_service=recipe_cleanup_service_dep,
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
    processing_service=recipe_processing_service_dep,
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
def get_recipe(recipe_id: str, recipe_manager=recipe_manager_dep) -> dict:
    """
    Get a complete recipe by its UUID.

    Returns the recipe with all ingredients and instructions,
    or 404 if the recipe is not found.
    """
    logger.info(f"Retrieving recipe with ID: {recipe_id}")

    try:
        recipe_data = recipe_manager.get_full_recipe(recipe_id)

        if not recipe_data:
            logger.warning(f"Recipe not found: {recipe_id}")
            raise HTTPException(status_code=404, detail="Recipe not found")

        logger.info(f"Successfully retrieved recipe: {recipe_id}")
        return {"recipe": recipe_data, "success": True}

    except Exception as e:
        logger.error(f"Error retrieving recipe {recipe_id}: {e!s}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving recipe: {e!s}"
        ) from e


@router.get("/health")
def health_check() -> dict:
    """
    Comprehensive health check including database connectivity.
    """
    try:
        # Check connection pool status
        pool_status = get_pool_status()

        # Try a simple database query
        with get_db_context() as (conn, cursor):
            cursor.execute("SELECT 1 as health_check")
            result = cursor.fetchone()
            db_healthy = result["health_check"] == 1

        status = (
            "healthy"
            if db_healthy and pool_status.get("pool_initialized")
            else "unhealthy"
        )

        return {
            "status": status,
            "database": {"connected": db_healthy, "pool": pool_status},
            "timestamp": "now()",
        }

    except Exception as e:
        logger.error(f"Health check failed: {e!s}")
        return {"status": "unhealthy", "error": str(e), "timestamp": "now()"}
