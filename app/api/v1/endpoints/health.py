from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix=settings.API_BASE_PATH, tags=["Health"])


@router.get("/")
def root():
    """Welcome message for the API root."""
    return {"message": "Welcome to ForkFolio API"}


@router.get("/health")
def health_check() -> dict:
    """
    Lightweight liveness check for load balancers and platform health probes.

    This endpoint intentionally avoids external dependencies (DB/LLM) so it can
    stay fast and resilient under load.
    """
    return {"status": "ok"}
