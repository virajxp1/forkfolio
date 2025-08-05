from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import setup_logging
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

    # Initialize database connection pool
    init_connection_pool()

    yield

    # Cleanup on shutdown
    close_connection_pool()


def create_application() -> FastAPI:
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

    @application.get("/health", tags=["Health"])
    def health_check():
        return {"status": "healthy"}

    return application


app = create_application()
