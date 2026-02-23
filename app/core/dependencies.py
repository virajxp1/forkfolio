"""
Dependency injection providers for the application.
"""

from app.services.data.managers.recipe_book_manager import RecipeBookManager
from app.services.data.managers.recipe_manager import RecipeManager
from app.services.recipe_embeddings_impl import RecipeEmbeddingsServiceImpl
from app.services.recipe_processing_service import RecipeProcessingService
from app.services.recipe_search_reranker_impl import RecipeSearchRerankerServiceImpl


def get_recipe_manager() -> RecipeManager:
    """
    Dependency provider for RecipeManager.

    Returns:
        RecipeManager instance
    """
    return RecipeManager()


def get_recipe_book_manager() -> RecipeBookManager:
    """
    Dependency provider for RecipeBookManager.

    Returns:
        RecipeBookManager instance
    """
    return RecipeBookManager()


def get_recipe_embeddings_service() -> RecipeEmbeddingsServiceImpl:
    """Dependency provider for RecipeEmbeddingsServiceImpl."""
    return RecipeEmbeddingsServiceImpl()


def get_recipe_search_reranker_service() -> RecipeSearchRerankerServiceImpl:
    """Dependency provider for RecipeSearchRerankerServiceImpl."""
    return RecipeSearchRerankerServiceImpl()


def get_recipe_processing_service() -> RecipeProcessingService:
    """Dependency provider for RecipeProcessingService."""
    return RecipeProcessingService()
