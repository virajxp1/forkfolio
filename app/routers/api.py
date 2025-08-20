from fastapi import APIRouter

from app.routers import health, recipes, recipe_utilities

# Main API router that includes all sub-routers
router = APIRouter()

# Include all sub-routers
router.include_router(health.router)
router.include_router(recipe_utilities.router)  # Temporary building blocks
router.include_router(recipes.router)  # Main recipe functionality
