from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import settings
from app.core.logging import get_logger
from app.services.data.supabase_client import get_db_context, get_pool_status

router = APIRouter(prefix=settings.API_V1_STR, tags=["Health"])
logger = get_logger(__name__)


@router.get("/")
def root():
    """Welcome message for the API root."""
    return {"message": "Welcome to ForkFolio API"}


@router.get("/health")
def health_check() -> dict:
    """
    Comprehensive health check including database connectivity.
    """
    try:
        # Check connection pool status
        pool_status = get_pool_status()

        # Try a simple database query
        with get_db_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 as health_check")
                result = cursor.fetchone()
                db_healthy = result["health_check"] == 1

        status = (
            "healthy"
            if db_healthy and pool_status.get("pool_initialized")
            else "unhealthy"
        )
        timestamp = datetime.now(timezone.utc).isoformat()

        return {
            "status": status,
            "database": {"connected": db_healthy, "pool": pool_status},
            "timestamp": timestamp,
        }

    except Exception as e:
        logger.error(f"Health check failed: {e!s}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
