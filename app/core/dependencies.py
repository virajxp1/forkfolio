"""
Dependency injection providers for the application.
"""

from app.services.recipe_extractor_impl import RecipeExtractorImpl
from app.services.recipe_input_cleanup_impl import RecipeInputCleanupServiceImpl


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
