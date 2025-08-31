from fastapi import APIRouter

from app.api.v1.endpoints import health, recipes, recipe_utilities

# Main API router that includes all sub-routers
router = APIRouter()

# Include all sub-routers
router.include_router(health.router)
router.include_router(recipe_utilities.router)
router.include_router(recipes.router)
