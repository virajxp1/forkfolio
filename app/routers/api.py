from fastapi import APIRouter

from app.core.config import settings
from app.services.llm_test_service import make_llm_call

router = APIRouter(prefix=settings.API_V1_STR)


@router.get("/")
def root():
    return {"message": "Welcome to ForkFolio API"}


@router.post("/llm-test")
def test_llm():
    return {"message": make_llm_call()}
