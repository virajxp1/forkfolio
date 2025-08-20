from fastapi import APIRouter, Body, Depends, HTTPException

from app.core.config import settings
from app.core.dependencies import (
    get_recipe_manager,
    get_recipe_processing_service,
)
from app.core.logging import get_logger
from app.api.schemas import RecipeIngestionRequest

router = APIRouter(prefix=f"{settings.API_V1_STR}/recipes", tags=["Recipes"])
logger = get_logger(__name__)

RECIPE_BODY = Body()

# Dependency instances to satisfy Ruff B008
recipe_manager_dep = Depends(get_recipe_manager)
recipe_processing_service_dep = Depends(get_recipe_processing_service)


@router.post("/process-and-store")
def process_and_store_recipe(
    ingestion_request: RecipeIngestionRequest = RECIPE_BODY,
    processing_service=recipe_processing_service_dep,
) -> dict:
    """
    Complete recipe processing pipeline: the main end-to-end recipe endpoint.

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


@router.get("/{recipe_id}")
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
