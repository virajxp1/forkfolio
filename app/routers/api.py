from fastapi import APIRouter

from app.api.v1.endpoints import health, recipe_books, recipes

# Main API router that includes all sub-routers
router = APIRouter()

# Include all sub-routers
router.include_router(health.router)
router.include_router(recipes.router)
router.include_router(recipe_books.router)
