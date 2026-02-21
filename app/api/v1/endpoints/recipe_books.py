from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.api.schemas import RecipeBookCreateRequest
from app.core.config import settings
from app.core.dependencies import get_recipe_book_manager
from app.core.logging import get_logger

router = APIRouter(
    prefix=f"{settings.API_V1_STR}/recipe-books",
    tags=["Recipe Books"],
)
logger = get_logger(__name__)

RECIPE_BOOK_BODY = Body()

# Dependency instances to satisfy Ruff B008
recipe_book_manager_dep = Depends(get_recipe_book_manager)


@router.post("/")
def create_recipe_book(
    recipe_book_request: RecipeBookCreateRequest = RECIPE_BOOK_BODY,
    recipe_book_manager=recipe_book_manager_dep,
) -> dict:
    """
    Create a recipe book.

    If a recipe book already exists for the same normalized name,
    returns the existing row with created=False.
    """
    try:
        recipe_book, created = recipe_book_manager.create_recipe_book(
            name=recipe_book_request.name,
            description=recipe_book_request.description,
        )
        return {
            "recipe_book": recipe_book,
            "created": created,
            "success": True,
        }
    except Exception as e:
        logger.exception("Error creating recipe book: %s", e)
        raise HTTPException(status_code=500, detail="Error creating recipe book") from e


@router.get("/")
def get_recipe_books(
    name: Optional[str] = Query(
        default=None,
        description="If provided, fetch a single recipe book by name",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of recipe books to return when listing",
    ),
    recipe_book_manager=recipe_book_manager_dep,
) -> dict:
    """
    List recipe books or fetch one by name.
    """
    try:
        if name:
            recipe_book = recipe_book_manager.get_full_recipe_book_by_name(name)
            if not recipe_book:
                raise HTTPException(status_code=404, detail="Recipe book not found")
            return {"recipe_book": recipe_book, "success": True}

        recipe_books = recipe_book_manager.list_recipe_books(limit=limit)
        return {"recipe_books": recipe_books, "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting recipe books: %s", e)
        raise HTTPException(status_code=500, detail="Error getting recipe books") from e


@router.get("/stats")
def get_recipe_book_stats(recipe_book_manager=recipe_book_manager_dep) -> dict:
    """
    Get aggregate recipe book statistics.
    """
    try:
        stats = recipe_book_manager.get_recipe_book_stats()
        return {"stats": stats, "success": True}
    except Exception as e:
        logger.exception("Error getting recipe book stats: %s", e)
        raise HTTPException(
            status_code=500, detail="Error getting recipe book stats"
        ) from e


@router.get("/by-recipe/{recipe_id}")
def get_recipe_books_for_recipe(
    recipe_id: UUID, recipe_book_manager=recipe_book_manager_dep
) -> dict:
    """
    Return all recipe books that include the given recipe.
    """
    recipe_id_str = str(recipe_id)
    try:
        if not recipe_book_manager.recipe_exists(recipe_id_str):
            raise HTTPException(status_code=404, detail="Recipe not found")

        recipe_books = recipe_book_manager.get_recipe_books_for_recipe(recipe_id_str)
        return {
            "recipe_id": recipe_id_str,
            "recipe_books": recipe_books,
            "success": True,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Error getting recipe books for recipe %s: %s", recipe_id_str, e
        )
        raise HTTPException(
            status_code=500,
            detail="Error getting recipe books for recipe",
        ) from e


@router.get("/{recipe_book_id}")
def get_recipe_book(
    recipe_book_id: UUID,
    recipe_book_manager=recipe_book_manager_dep,
) -> dict:
    """
    Get a recipe book by ID, including recipe IDs.
    """
    recipe_book_id_str = str(recipe_book_id)
    try:
        recipe_book = recipe_book_manager.get_full_recipe_book_by_id(recipe_book_id_str)
        if not recipe_book:
            raise HTTPException(status_code=404, detail="Recipe book not found")

        return {"recipe_book": recipe_book, "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting recipe book %s: %s", recipe_book_id_str, e)
        raise HTTPException(status_code=500, detail="Error getting recipe book") from e


@router.put("/{recipe_book_id}/recipes/{recipe_id}")
def add_recipe_to_book(
    recipe_book_id: UUID,
    recipe_id: UUID,
    recipe_book_manager=recipe_book_manager_dep,
) -> dict:
    """
    Add a recipe to a recipe book (idempotent).
    """
    recipe_book_id_str = str(recipe_book_id)
    recipe_id_str = str(recipe_id)
    try:
        result = recipe_book_manager.add_recipe_to_book(
            recipe_book_id_str, recipe_id_str
        )
        if not result["book_exists"]:
            raise HTTPException(status_code=404, detail="Recipe book not found")
        if not result["recipe_exists"]:
            raise HTTPException(status_code=404, detail="Recipe not found")

        return {
            "recipe_book_id": recipe_book_id_str,
            "recipe_id": recipe_id_str,
            "added": result["added"],
            "success": True,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Error adding recipe %s to recipe book %s: %s",
            recipe_id_str,
            recipe_book_id_str,
            e,
        )
        raise HTTPException(
            status_code=500, detail="Error adding recipe to recipe book"
        ) from e


@router.delete("/{recipe_book_id}/recipes/{recipe_id}")
def remove_recipe_from_book(
    recipe_book_id: UUID,
    recipe_id: UUID,
    recipe_book_manager=recipe_book_manager_dep,
) -> dict:
    """
    Remove a recipe from a recipe book.
    """
    recipe_book_id_str = str(recipe_book_id)
    recipe_id_str = str(recipe_id)
    try:
        result = recipe_book_manager.remove_recipe_from_book(
            recipe_book_id_str, recipe_id_str
        )
        if not result["book_exists"]:
            raise HTTPException(status_code=404, detail="Recipe book not found")

        return {
            "recipe_book_id": recipe_book_id_str,
            "recipe_id": recipe_id_str,
            "removed": result["removed"],
            "success": True,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Error removing recipe %s from recipe book %s: %s",
            recipe_id_str,
            recipe_book_id_str,
            e,
        )
        raise HTTPException(
            status_code=500,
            detail="Error removing recipe from recipe book",
        ) from e
