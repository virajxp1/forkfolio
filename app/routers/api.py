from fastapi import APIRouter, Query

from app.core.config import settings
from app.services.location_llm_test_example_service import LocationLLMTestExampleService

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
