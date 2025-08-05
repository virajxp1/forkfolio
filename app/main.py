from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from app.core.config import settings
from app.routers import api


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load environment variables on startup
    load_dotenv()
    yield


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
