"""
Dependency injection providers for the application.
"""

from app.services.data.managers.recipe_manager import RecipeManager
from app.services.recipe_extractor_impl import RecipeExtractorImpl
from app.services.recipe_input_cleanup_impl import RecipeInputCleanupServiceImpl
from app.services.recipe_processing_service import RecipeProcessingService


def get_recipe_extractor() -> RecipeExtractorImpl:
    """
    Dependency provider for RecipeExtractorImpl.

    Returns:
        RecipeExtractorImpl instance
    """
    return RecipeExtractorImpl()


def get_recipe_cleanup_service() -> RecipeInputCleanupServiceImpl:
    """
    Dependency provider for RecipeInputCleanupServiceImpl.

    Returns:
        RecipeInputCleanupServiceImpl instance
    """
    return RecipeInputCleanupServiceImpl()


def get_recipe_manager() -> RecipeManager:
    """
    Dependency provider for RecipeManager.

    Returns:
        RecipeManager instance
    """
    return RecipeManager()


def get_recipe_processing_service() -> RecipeProcessingService:
    """
    Dependency provider for RecipeProcessingService.

    Returns:
        RecipeProcessingService instance
    """
    cleanup_service = get_recipe_cleanup_service()
    extractor_service = get_recipe_extractor()
    recipe_manager = get_recipe_manager()
    return RecipeProcessingService(
        cleanup_service=cleanup_service,
        extractor_service=extractor_service,
        recipe_manager=recipe_manager,
    )
