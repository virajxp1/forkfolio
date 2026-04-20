from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request

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
from app.api.v1.helpers.recipe_pagination import RecipePaginationCursor
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


def _semantic_search_cache_key(
    normalized_query: str,
    limit: int,
    include_test_data: bool,
    rerank_enabled: bool,
    viewer_user_id: str | None,
) -> str:
    return hash_cache_key(
        "semantic_search",
        normalized_query,
        str(limit),
        str(include_test_data),
        viewer_user_id or "public-only",
        str(settings.SEMANTIC_SEARCH_MAX_DISTANCE),
        str(rerank_enabled),
        str(settings.SEMANTIC_SEARCH_RERANK_CANDIDATE_COUNT),
        str(settings.SEMANTIC_SEARCH_RERANK_MIN_SCORE),
        str(settings.SEMANTIC_SEARCH_RERANK_FALLBACK_MIN_SCORE),
        str(settings.SEMANTIC_SEARCH_RERANK_WEIGHT),
        str(settings.SEMANTIC_SEARCH_RERANK_CUISINE_BOOST),
        str(settings.SEMANTIC_SEARCH_RERANK_FAMILY_BOOST),
    )


def _viewer_user_id_from_request(request: Request) -> str | None:
    raw_value = request.headers.get("x-viewer-user-id", "").strip()
    if not raw_value:
        return None
    try:
        return str(UUID(raw_value))
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="Invalid X-Viewer-User-Id header"
        ) from exc


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
    source_url = (
        str(ingestion_request.source_url) if ingestion_request.source_url else None
    )
    created_by_user_id = (
        str(ingestion_request.created_by_user_id)
        if ingestion_request.created_by_user_id
        else None
    )
    recipe_id, error, created = processing_service.process_raw_recipe(
        raw_input=ingestion_request.raw_input,
        source_url=source_url,
        enforce_deduplication=ingestion_request.enforce_deduplication,
        is_test=ingestion_request.is_test,
        is_public=ingestion_request.is_public,
        created_by_user_id=created_by_user_id,
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
        recipe_data = recipe_manager.get_full_recipe(
            recipe_id,
            include_test_data=ingestion_request.is_test,
            viewer_user_id=created_by_user_id,
        )
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

    recipe_data = recipe_manager.get_full_recipe(
        recipe_id,
        include_test_data=ingestion_request.is_test,
        viewer_user_id=created_by_user_id,
    )
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
    request: Request,
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
    include_test_data: bool = Query(
        default=False,
        description="Include recipes marked as test data.",
    ),
    recipe_manager=recipe_manager_dep,
) -> dict:
    """
    List recipes with cursor-based pagination.
    """
    cursor_created_at = None
    cursor_id = None
    viewer_user_id = _viewer_user_id_from_request(request)

    if cursor:
        try:
            cursor_created_at, cursor_id = RecipePaginationCursor.decode(cursor)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid cursor value") from exc

    try:
        page_with_sentinel = recipe_manager.list_recipes_page(
            limit=limit + 1,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
            include_test_data=include_test_data,
            viewer_user_id=viewer_user_id,
        )
        has_more = len(page_with_sentinel) > limit
        recipes_page = page_with_sentinel[:limit]

        next_cursor = None
        if has_more and recipes_page:
            last_recipe = recipes_page[-1]
            next_cursor = RecipePaginationCursor.encode(
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
    request: Request,
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
    include_test_data: bool = Query(
        default=False,
        description="Include recipes marked as test data.",
    ),
    rerank: bool | None = Query(
        default=None,
        description=(
            "Override reranking for this request. Set false for the fastest path, "
            "or true to force LLM reranking."
        ),
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
    rerank_enabled = (
        settings.SEMANTIC_SEARCH_RERANK_ENABLED if rerank is None else rerank
    )
    viewer_user_id = _viewer_user_id_from_request(request)
    cache_key = _semantic_search_cache_key(
        normalized_query=normalized_query,
        limit=limit,
        include_test_data=include_test_data,
        rerank_enabled=rerank_enabled,
        viewer_user_id=viewer_user_id,
    )
    cached_response = semantic_search_cache.get(cache_key)
    if cached_response is not None:
        logger.info(
            "Semantic recipe search cache hit query='%s' limit=%s rerank=%s",
            normalized_query,
            limit,
            rerank_enabled,
        )
        return cached_response

    logger.info(
        "Semantic recipe search query='%s' limit=%s rerank=%s max_distance=%.3f",
        normalized_query,
        limit,
        rerank_enabled,
        settings.SEMANTIC_SEARCH_MAX_DISTANCE,
    )
    try:
        query_embedding = embeddings_service.embed_search_query(normalized_query)
        candidate_limit = limit
        if rerank_enabled:
            candidate_limit = max(
                limit, settings.SEMANTIC_SEARCH_RERANK_CANDIDATE_COUNT
            )
        matches = recipe_manager.search_recipes_by_embedding(
            embedding=query_embedding,
            embedding_type="title_ingredients",
            limit=candidate_limit,
            max_distance=settings.SEMANTIC_SEARCH_MAX_DISTANCE,
            include_test_data=include_test_data,
            viewer_user_id=viewer_user_id,
        )
        if rerank_enabled and len(matches) > 1:
            ranked_items = []
            try:
                rerank_candidates = build_rerank_candidates(
                    matches,
                    recipe_manager,
                    include_test_data=include_test_data,
                    viewer_user_id=viewer_user_id,
                )
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


@router.get("/search/by-name")
def search_recipes_by_name(
    request: Request,
    query: str = Query(
        ...,
        min_length=3,
        description="Case-insensitive substring match against recipe titles.",
    ),
    limit: int = Query(
        10,
        ge=1,
        le=10,
        description="Maximum number of title matches to return.",
    ),
    include_test_data: bool = Query(
        default=False,
        description="Include recipes marked as test data.",
    ),
    recipe_manager=recipe_manager_dep,
) -> dict:
    normalized_query = normalize_search_query(query)
    viewer_user_id = _viewer_user_id_from_request(request)
    if len(normalized_query) < 3:
        raise HTTPException(
            status_code=422,
            detail="Query must contain at least 3 non-whitespace characters.",
        )

    try:
        matches = recipe_manager.find_recipes_by_title_query(
            title_query=normalized_query,
            limit=limit,
            include_test_data=include_test_data,
            viewer_user_id=viewer_user_id,
        )
        results = [
            {
                "id": match["id"],
                "name": match["title"],
                "distance": None,
            }
            for match in matches
        ]
        return {
            "query": normalized_query,
            "count": len(results),
            "results": results,
            "success": True,
        }
    except Exception as e:
        logger.error(f"Error performing recipe title search: {e!s}")
        raise HTTPException(
            status_code=500,
            detail=f"Error performing recipe title search: {e!s}",
        ) from e


@router.post("/grocery-list")
def create_grocery_list(
    request: Request,
    grocery_list_request: GroceryListCreateRequest = GROCERY_LIST_BODY,
    include_test_data: bool = Query(
        default=False,
        description="Include recipes marked as test data.",
    ),
    recipe_manager=recipe_manager_dep,
    grocery_list_aggregation_service=grocery_list_aggregation_service_dep,
) -> dict:
    """
    Create one aggregated grocery list from many recipe IDs.
    """
    recipe_ids = list(
        dict.fromkeys(str(recipe_id) for recipe_id in grocery_list_request.recipe_ids)
    )
    viewer_user_id = _viewer_user_id_from_request(request)
    try:
        ingredients_by_recipe = recipe_manager.get_ingredients_for_recipes(
            recipe_ids,
            include_test_data=include_test_data,
            viewer_user_id=viewer_user_id,
        )
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
def get_recipe(
    request: Request,
    recipe_id: str,
    include_test_data: bool = Query(
        default=False,
        description="Include recipes marked as test data.",
    ),
    recipe_manager=recipe_manager_dep,
) -> dict:
    """
    Get a complete recipe by its UUID.

    Returns the recipe with all ingredients and instructions,
    or 404 if the recipe is not found.
    """
    logger.info(f"Retrieving recipe with ID: {recipe_id}")
    viewer_user_id = _viewer_user_id_from_request(request)

    try:
        recipe_data = recipe_manager.get_full_recipe(
            recipe_id,
            include_test_data=include_test_data,
            viewer_user_id=viewer_user_id,
        )

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
def get_recipe_all(
    request: Request,
    recipe_id: str,
    include_test_data: bool = Query(
        default=False,
        description="Include recipes marked as test data.",
    ),
    recipe_manager=recipe_manager_dep,
) -> dict:
    """
    Get a complete recipe by its UUID, including embeddings.

    Returns the recipe with ingredients, instructions, and embeddings,
    or 404 if the recipe is not found.
    """
    logger.info(f"Retrieving full recipe with embeddings for ID: {recipe_id}")
    viewer_user_id = _viewer_user_id_from_request(request)

    try:
        recipe_data = recipe_manager.get_full_recipe_with_embeddings(
            recipe_id,
            include_test_data=include_test_data,
            viewer_user_id=viewer_user_id,
        )

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
