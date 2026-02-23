from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.api.schemas import RecipeIngestionRequest
from app.api.v1.helpers.recipe_search import (
    apply_rerank,
    build_rerank_candidates,
    normalize_search_query,
)
from app.core.config import settings
from app.core.dependencies import (
    get_recipe_embeddings_service,
    get_recipe_manager,
    get_recipe_processing_service,
    get_recipe_search_reranker_service,
)
from app.core.logging import get_logger

router = APIRouter(prefix=f"{settings.API_BASE_PATH}/recipes", tags=["Recipes"])
logger = get_logger(__name__)

RECIPE_BODY = Body()

# Dependency instances to satisfy Ruff B008
recipe_manager_dep = Depends(get_recipe_manager)
recipe_processing_service_dep = Depends(get_recipe_processing_service)
recipe_embeddings_service_dep = Depends(get_recipe_embeddings_service)
recipe_search_reranker_service_dep = Depends(get_recipe_search_reranker_service)


@router.post("/process-and-store")
def process_and_store_recipe(
    ingestion_request: RecipeIngestionRequest = RECIPE_BODY,
    processing_service=recipe_processing_service_dep,
    recipe_manager=recipe_manager_dep,
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
    recipe_id, error, created = processing_service.process_raw_recipe(
        raw_input=ingestion_request.raw_input,
        source_url=None,  # Could extend request model to include source_url if needed
        enforce_deduplication=ingestion_request.enforce_deduplication,
        is_test=ingestion_request.is_test,
    )

    if error:
        return {"error": error, "success": False}

    if not created:
        if not recipe_id:
            logger.error("Duplicate recipe detected but no recipe_id was returned")
            return {
                "error": "Duplicate recipe detected but no recipe_id was returned",
                "success": False,
            }
        recipe_data = recipe_manager.get_full_recipe(recipe_id)
        if not recipe_data:
            logger.error(f"Duplicate recipe found but not retrieved: {recipe_id}")
            raise HTTPException(
                status_code=500,
                detail="Duplicate recipe found but could not be retrieved",
            )
        logger.info(f"Duplicate recipe found; returning existing recipe: {recipe_id}")
        return {
            "recipe_id": recipe_id,
            "recipe": recipe_data,
            "success": True,
            "created": False,
            "message": "Duplicate recipe found; returning existing recipe.",
        }

    recipe_data = recipe_manager.get_full_recipe(recipe_id)
    if not recipe_data:
        logger.error(f"Recipe stored but not found: {recipe_id}")
        raise HTTPException(
            status_code=500,
            detail="Recipe stored but could not be retrieved",
        )

    return {
        "recipe_id": recipe_id,
        "recipe": recipe_data,
        "success": True,
        "created": True,
        "message": "Recipe processed and stored successfully",
    }


@router.get("/search/semantic")
def semantic_search_recipes(
    query: str = Query(
        ...,
        min_length=2,
        description="Free-text recipe query for vector similarity search.",
    ),
    limit: int = Query(
        10,
        ge=1,
        le=50,
        description="Maximum number of similar recipes to return.",
    ),
    recipe_manager=recipe_manager_dep,
    embeddings_service=recipe_embeddings_service_dep,
    reranker_service=recipe_search_reranker_service_dep,
) -> dict:
    """
    Semantic search over recipes using title+ingredients embeddings.

    Uses a server-side cosine distance threshold and returns nearest recipe hits
    with lightweight metadata and cosine distance.
    """
    normalized_query = normalize_search_query(query)
    if len(normalized_query) < 2:
        raise HTTPException(
            status_code=422,
            detail="Query must contain at least 2 non-whitespace characters.",
        )

    logger.info(
        "Semantic recipe search query='%s' limit=%s max_distance=%.3f",
        normalized_query,
        limit,
        settings.SEMANTIC_SEARCH_MAX_DISTANCE,
    )
    try:
        query_embedding = embeddings_service.embed_search_query(normalized_query)
        candidate_limit = limit
        if settings.SEMANTIC_SEARCH_RERANK_ENABLED:
            candidate_limit = max(
                limit, settings.SEMANTIC_SEARCH_RERANK_CANDIDATE_COUNT
            )
        matches = recipe_manager.search_recipes_by_embedding(
            embedding=query_embedding,
            embedding_type="title_ingredients",
            limit=candidate_limit,
            max_distance=settings.SEMANTIC_SEARCH_MAX_DISTANCE,
        )
        if settings.SEMANTIC_SEARCH_RERANK_ENABLED and len(matches) > 1:
            ranked_items = []
            try:
                rerank_candidates = build_rerank_candidates(matches, recipe_manager)
                ranked_items = reranker_service.rerank(
                    query=normalized_query,
                    candidates=rerank_candidates,
                    max_results=limit,
                )
            except Exception as exc:
                logger.warning(
                    "Rerank execution failed; falling back to embedding order. Error: %s",
                    exc,
                )
            matches = apply_rerank(
                matches,
                ranked_items,
                limit,
                min_rerank_score=settings.SEMANTIC_SEARCH_RERANK_MIN_SCORE,
                fallback_min_rerank_score=(
                    settings.SEMANTIC_SEARCH_RERANK_FALLBACK_MIN_SCORE
                ),
                rerank_weight=settings.SEMANTIC_SEARCH_RERANK_WEIGHT,
                query=normalized_query,
                cuisine_boost=settings.SEMANTIC_SEARCH_RERANK_CUISINE_BOOST,
                family_boost=settings.SEMANTIC_SEARCH_RERANK_FAMILY_BOOST,
            )
        else:
            matches = matches[:limit]
        return {
            "query": normalized_query,
            "count": len(matches),
            "results": matches,
            "success": True,
        }
    except Exception as e:
        logger.error(f"Error performing semantic recipe search: {e!s}")
        raise HTTPException(
            status_code=500,
            detail=f"Error performing semantic search: {e!s}",
        ) from e


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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving recipe {recipe_id}: {e!s}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving recipe: {e!s}"
        ) from e


@router.get("/{recipe_id}/all")
def get_recipe_all(recipe_id: str, recipe_manager=recipe_manager_dep) -> dict:
    """
    Get a complete recipe by its UUID, including embeddings.

    Returns the recipe with ingredients, instructions, and embeddings,
    or 404 if the recipe is not found.
    """
    logger.info(f"Retrieving full recipe with embeddings for ID: {recipe_id}")

    try:
        recipe_data = recipe_manager.get_full_recipe_with_embeddings(recipe_id)

        if not recipe_data:
            logger.warning(f"Recipe not found: {recipe_id}")
            raise HTTPException(status_code=404, detail="Recipe not found")

        logger.info(f"Successfully retrieved full recipe: {recipe_id}")
        return {"recipe": recipe_data, "success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving recipe {recipe_id}: {e!s}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving recipe: {e!s}"
        ) from e


@router.delete("/delete/{recipe_id}")
def delete_recipe(recipe_id: str, recipe_manager=recipe_manager_dep) -> bool:
    """
    Delete a recipe by its UUID.
    returns true on success
    """
    logger.info(f"Deleting recipe with ID: {recipe_id}")
    try:
        deleted = recipe_manager.delete_recipe(recipe_id)
        if not deleted:
            logger.warning(f"Recipe not found for delete: {recipe_id}")
            raise HTTPException(status_code=404, detail="Recipe not found")
        return True
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting recipe {recipe_id}: {e!s}")
        raise HTTPException(
            status_code=500, detail=f"Error deleting recipe: {e!s}"
        ) from e
