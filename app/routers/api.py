from typing import Union

from fastapi import APIRouter, Body, Query

from app.core.config import settings
from app.core.test_inputs import RAW_RECIPE_BODY
from app.schemas.ingest import RecipeIngestionRequest
from app.schemas.recipe import Recipe, RecipeCleanupRequest, RecipeCleanupResponse
from app.services import RecipeInputCleanupImpl
from app.services.location_llm_test_example_service import LocationLLMTestExampleService
from app.services.recipe_extractor_impl import RecipeExtractorImpl

router = APIRouter(prefix=settings.API_V1_STR)

RECIPE_BODY = Body()


@router.get("/")
def root():
    return {"message": "Welcome to ForkFolio API"}


@router.post("/ingest-raw-recipe")
def ingest_raw_recipe(
    ingestion_input_request: RecipeIngestionRequest = RECIPE_BODY,
) -> Union[Recipe, dict]:
    """
    Extract structured recipe data from raw text input.

    Takes unstructured recipe text and returns a structured Recipe object
    with title, ingredients, instructions, servings, and timing information.
    If extraction fails, returns an error response.
    """
    ## TODO - Need to use dependency injection
    recipe_extractor = RecipeExtractorImpl()
    extracted_recipe, error = recipe_extractor.extract_recipe_from_raw_text(
        ingestion_input_request.raw_input
    )

    if error:
        return {"error": error, "success": False}

    return extracted_recipe


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
    ## TODO - Need to use dependency injection
    location_service = LocationLLMTestExampleService()
    location_info = location_service.get_location_info(location)
    return location_info


@router.post("/cleanup-raw-recipe", response_model=RecipeCleanupResponse)
def recipe_cleanup(
    cleanup_request: RecipeCleanupRequest = Body(),
) -> RecipeCleanupResponse:
    """
    Clean up messy recipe input data (HTML, scraped content, etc.)
    and return cleaned text suitable for recipe extraction.
    """
    # TODO - Need to use dependency injection
    recipe_cleanup_service = RecipeInputCleanupImpl()
    cleaned_text = recipe_cleanup_service.cleanup_input(cleanup_request.raw_text)

    return RecipeCleanupResponse(
        cleaned_text=cleaned_text,
        source_url=cleanup_request.source_url,
        original_length=len(cleanup_request.raw_text),
        cleaned_length=len(cleaned_text),
    )
