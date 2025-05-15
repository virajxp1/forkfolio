from fastapi import APIRouter

from app.core.config import settings
from app.services.llm_test_service import (
    make_llm_call_structured_output,
    make_llm_call_text_generation,
)

router = APIRouter(prefix=settings.API_V1_STR)


@router.get("/")
def root():
    return {"message": "Welcome to ForkFolio API"}


@router.post("/llm-test")
def test_llm():
    return {"message": make_llm_call_text_generation()}


@router.post("/llm-test-structured")
def test_llm_structured():
    return make_llm_call_structured_output()
