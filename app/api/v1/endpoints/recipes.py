import base64
import binascii
import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.api.schemas import (
    GroceryListCreateRequest,
    RecipeIngestionRequest,
    RecipeUrlPreviewRequest,
)
from app.api.v1.helpers.recipe_search import (
    apply_rerank,
    build_rerank_candidates,
    normalize_search_query,
)
from app.core.cache import hash_cache_key, semantic_search_cache
from app.core.config import settings
from app.core.dependencies import (
    get_grocery_list_aggregation_service,
    get_recipe_embeddings_service,
    get_recipe_manager,
    get_recipe_processing_service,
    get_recipe_search_reranker_service,
)
from app.core.logging import get_logger

router = APIRouter(prefix=f"{settings.API_BASE_PATH}/recipes", tags=["Recipes"])
logger = get_logger(__name__)

RECIPE_BODY = Body()
GROCERY_LIST_BODY = Body()

# Dependency instances to satisfy Ruff B008
recipe_manager_dep = Depends(get_recipe_manager)
recipe_processing_service_dep = Depends(get_recipe_processing_service)
recipe_embeddings_service_dep = Depends(get_recipe_embeddings_service)
recipe_search_reranker_service_dep = Depends(get_recipe_search_reranker_service)
grocery_list_aggregation_service_dep = Depends(get_grocery_list_aggregation_service)


def _semantic_search_cache_key(normalized_query: str, limit: int) -> str:
    return hash_cache_key(
        "semantic_search",
        normalized_query,
        str(limit),
        str(settings.SEMANTIC_SEARCH_MAX_DISTANCE),
        str(settings.SEMANTIC_SEARCH_RERANK_ENABLED),
        str(settings.SEMANTIC_SEARCH_RERANK_CANDIDATE_COUNT),
        str(settings.SEMANTIC_SEARCH_RERANK_MIN_SCORE),
        str(settings.SEMANTIC_SEARCH_RERANK_FALLBACK_MIN_SCORE),
        str(settings.SEMANTIC_SEARCH_RERANK_WEIGHT),
        str(settings.SEMANTIC_SEARCH_RERANK_CUISINE_BOOST),
        str(settings.SEMANTIC_SEARCH_RERANK_FAMILY_BOOST),
    )


def _encode_recipe_page_cursor(created_at: datetime, recipe_id: str) -> str:
    if not isinstance(created_at, datetime):
        raise ValueError("Cursor created_at must be a datetime")

    payload = {
        "created_at": created_at.isoformat(),
        "id": recipe_id,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _decode_recipe_page_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        normalized_cursor = cursor.strip()
        if not normalized_cursor:
            raise ValueError("Cursor cannot be empty")
        padded_cursor = normalized_cursor + "=" * (-len(normalized_cursor) % 4)
        decoded = base64.urlsafe_b64decode(padded_cursor.encode("utf-8")).decode(
            "utf-8"
        )
        payload = json.loads(decoded)
        created_at_value = datetime.fromisoformat(payload["created_at"])
        recipe_id = str(UUID(str(payload["id"])))
        return created_at_value, recipe_id
    except (
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        binascii.Error,
    ) as exc:
        raise ValueError("Invalid cursor") from exc


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
    semantic_search_cache.clear()

    return {
        "recipe_id": recipe_id,
        "recipe": recipe_data,
        "success": True,
        "created": True,
        "message": "Recipe processed and stored successfully",
    }


@router.post("/preview-from-url")
def preview_recipe_from_url(
    preview_request: RecipeUrlPreviewRequest = RECIPE_BODY,
    processing_service=recipe_processing_service_dep,
) -> dict:
    """
    Fetch a URL and run the cleanup+extraction pipeline without storing data.

    Returns a recipe preview payload suitable for user confirmation prior to
    calling process-and-store.
    """
    source_url = str(preview_request.url)
    recipe, error, diagnostics = processing_service.preview_recipe_from_url(source_url)

    if error:
        return {
            "success": False,
            "created": False,
            "url": source_url,
            "diagnostics": diagnostics,
            "error": error,
        }
    if not recipe:
        return {
            "success": False,
            "created": False,
            "url": source_url,
            "diagnostics": diagnostics,
            "error": "Recipe preview did not return data",
        }

    return {
        "success": True,
        "created": False,
        "url": source_url,
        "recipe_preview": recipe.model_dump(),
        "diagnostics": diagnostics,
        "message": (
            "Recipe preview generated successfully. No database insertion performed."
        ),
    }


@router.get("/")
def list_recipes(
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of recipes to return in one page.",
    ),
    cursor: str | None = Query(
        default=None,
        description=(
            "Opaque cursor token from the previous response for paginated listing."
        ),
    ),
    recipe_manager=recipe_manager_dep,
) -> dict:
    """
    List recipes with cursor-based pagination.
    """
    cursor_created_at = None
    cursor_id = None

    if cursor:
        try:
            cursor_created_at, cursor_id = _decode_recipe_page_cursor(cursor)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid cursor value") from exc

    try:
        page_with_sentinel = recipe_manager.list_recipes_page(
            limit=limit + 1,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
        has_more = len(page_with_sentinel) > limit
        recipes_page = page_with_sentinel[:limit]

        next_cursor = None
        if has_more and recipes_page:
            last_recipe = recipes_page[-1]
            next_cursor = _encode_recipe_page_cursor(
                last_recipe["created_at"],
                str(last_recipe["id"]),
            )

        return {
            "recipes": recipes_page,
            "count": len(recipes_page),
            "limit": limit,
            "cursor": cursor,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "success": True,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error listing recipes: %s", e)
        raise HTTPException(status_code=500, detail="Error listing recipes") from e


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
    cache_key = _semantic_search_cache_key(normalized_query, limit)
    cached_response = semantic_search_cache.get(cache_key)
    if cached_response is not None:
        logger.info(
            "Semantic recipe search cache hit query='%s' limit=%s",
            normalized_query,
            limit,
        )
        return cached_response

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
        response_payload = {
            "query": normalized_query,
            "count": len(matches),
            "results": matches,
            "success": True,
        }
        semantic_search_cache.set(cache_key, response_payload)
        return response_payload
    except Exception as e:
        logger.error(f"Error performing semantic recipe search: {e!s}")
        raise HTTPException(
            status_code=500,
            detail=f"Error performing semantic search: {e!s}",
        ) from e


@router.post("/grocery-list")
def create_grocery_list(
    grocery_list_request: GroceryListCreateRequest = GROCERY_LIST_BODY,
    recipe_manager=recipe_manager_dep,
    grocery_list_aggregation_service=grocery_list_aggregation_service_dep,
) -> dict:
    """
    Create one aggregated grocery list from many recipe IDs.
    """
    recipe_ids = list(
        dict.fromkeys(str(recipe_id) for recipe_id in grocery_list_request.recipe_ids)
    )
    try:
        ingredients_by_recipe = recipe_manager.get_ingredients_for_recipes(recipe_ids)
        missing_recipe_ids = [
            recipe_id
            for recipe_id in recipe_ids
            if recipe_id not in ingredients_by_recipe
        ]
        if missing_recipe_ids:
            missing_text = ", ".join(missing_recipe_ids)
            raise HTTPException(
                status_code=404,
                detail=f"Recipes not found: {missing_text}",
            )

        all_ingredients: list[str] = []
        for recipe_id in recipe_ids:
            all_ingredients.extend(ingredients_by_recipe.get(recipe_id, []))

        grocery_ingredients, error = (
            grocery_list_aggregation_service.aggregate_ingredients(all_ingredients)
        )
        if error or grocery_ingredients is None:
            logger.error("Error generating grocery list: %s", error)
            raise HTTPException(
                status_code=500,
                detail="Error generating grocery list",
            )

        return {
            "recipe_ids": recipe_ids,
            "ingredients": grocery_ingredients,
            "count": len(grocery_ingredients),
            "success": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error generating grocery list: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Error generating grocery list",
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
