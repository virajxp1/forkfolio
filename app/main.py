from fastapi import FastAPI
from app.routers import api
from app.core.config import settings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Include routers
    application.include_router(api.router)
    
    @application.get("/health", tags=["Health"])
    def health_check():
        return {"status": "healthy"}
    
    return application

app = create_application()
