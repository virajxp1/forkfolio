"""
Dependency injection providers for the application.
"""

from app.services.experiment_service import ExperimentService
from app.services.data.managers.experiment_manager import ExperimentManager
from app.services.data.managers.recipe_book_manager import RecipeBookManager
from app.services.data.managers.recipe_manager import RecipeManager
from app.services.grocery_list_aggregation_impl import GroceryListAggregationServiceImpl
from app.services.recipe_embeddings_impl import RecipeEmbeddingsServiceImpl
from app.services.recipe_hybrid_search_impl import RecipeHybridSearchServiceImpl
from app.services.recipe_processing_service import RecipeProcessingService


def get_recipe_manager() -> RecipeManager:
    """
    Dependency provider for RecipeManager.

    Returns:
        RecipeManager instance
    """
    return RecipeManager()


def get_experiment_manager() -> ExperimentManager:
    """Dependency provider for ExperimentManager."""
    return ExperimentManager()


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


def get_recipe_hybrid_search_service() -> RecipeHybridSearchServiceImpl:
    """Dependency provider for the Postgres hybrid search service."""
    return RecipeHybridSearchServiceImpl()


def get_grocery_list_aggregation_service() -> GroceryListAggregationServiceImpl:
    """Dependency provider for GroceryListAggregationServiceImpl."""
    return GroceryListAggregationServiceImpl()


def get_recipe_processing_service() -> RecipeProcessingService:
    """Dependency provider for RecipeProcessingService."""
    return RecipeProcessingService()


def get_experiment_service() -> ExperimentService:
    """Dependency provider for ExperimentService."""
    return ExperimentService(
        experiment_manager=get_experiment_manager(),
        recipe_manager=get_recipe_manager(),
        recipe_embeddings_service=get_recipe_embeddings_service(),
        recipe_hybrid_search_service=get_recipe_hybrid_search_service(),
    )
