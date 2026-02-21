from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.middleware import (
    AuthTokenMiddleware,
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    RequestTimeoutMiddleware,
)
from app.routers import api
from app.services.data.supabase_client import (
    close_connection_pool,
    init_connection_pool,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load environment variables on startup
    load_dotenv()

    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    logger.info(
        "Request protection: rate_limit_per_min=%s max_body_mb=%s timeout_s=%s",
        settings.RATE_LIMIT_PER_MINUTE,
        settings.MAX_REQUEST_SIZE_MB,
        settings.REQUEST_TIMEOUT_SECONDS,
    )
    if settings.API_AUTH_TOKEN:
        logger.info("API auth token: enabled")
    else:
        logger.warning("API auth token: disabled")

    # Initialize database connection pool
    init_connection_pool()

    yield

    # Cleanup on shutdown
    close_connection_pool()


def _public_paths(api_root_path: str) -> tuple[str, ...]:
    return (
        api_root_path,
        f"{api_root_path}/health",
    )


def create_application() -> FastAPI:
    api_root_path = settings.API_BASE_PATH
    public_paths = _public_paths(api_root_path)

    application = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Include routers
    application.include_router(api.router)

    # Middleware (added in order from innermost to outermost)
    application.add_middleware(
        RequestTimeoutMiddleware, timeout_seconds=settings.REQUEST_TIMEOUT_SECONDS
    )
    application.add_middleware(
        AuthTokenMiddleware,
        token=settings.API_AUTH_TOKEN,
        exempt_paths=public_paths,
    )
    application.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        exempt_paths=public_paths,
    )
    application.add_middleware(
        RequestSizeLimitMiddleware,
        max_body_size_bytes=settings.MAX_REQUEST_SIZE_MB * 1024 * 1024,
    )

    return application


app = create_application()
