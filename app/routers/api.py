from fastapi import APIRouter, Query

from app.core.config import settings
from app.schemas.recipe import (
    RAW_RECIPE_BODY,
    RecipeCleanupRequest,
    RecipeCleanupResponse,
)
from app.services.location_llm_test_example_service import LocationLLMTestExampleService
from app.services.recipe_input_cleanup_impl import RecipeInputCleanupImpl

router = APIRouter(prefix=settings.API_V1_STR)


@router.get("/")
def root():
    return {"message": "Welcome to ForkFolio API"}


@router.post("/llm-test")
def test_llm(country: str = Query("France", description="Country to get capital for")):
    location_service = LocationLLMTestExampleService()
    capital = location_service.get_capital(country)
    return {"capital": capital, "country": country}


@router.post("/llm-test-structured")
def test_llm_structured(
    location: str = Query(
        "New York City, USA", description="Location to extract information about"
    ),
):
    location_service = LocationLLMTestExampleService()
    location_info = location_service.get_location_info(location)
    return location_info


@router.post("/ingest-raw-recipe", response_model=RecipeCleanupResponse)
def ingest_raw_recipe(
    cleanup_request: RecipeCleanupRequest = RAW_RECIPE_BODY,
) -> RecipeCleanupResponse:
    """
    Clean up messy recipe input data (HTML, scraped content, etc.)
    and return cleaned text suitable for recipe extraction.
    """
    # TODO - Need to use dependency injection
    recipe_cleanup = RecipeInputCleanupImpl()
    cleaned_text = recipe_cleanup.cleanup_input(cleanup_request.raw_text)

    return RecipeCleanupResponse(
        cleaned_text=cleaned_text,
        source_url=cleanup_request.source_url,
        original_length=len(cleanup_request.raw_text),
        cleaned_length=len(cleaned_text),
    )
