"""
Main API client that combines all endpoint clients.

This provides a single entry point for all API interactions during testing,
with each endpoint group accessible as a separate client instance.
"""

from .health_client import HealthClient
from .recipe_utilities_client import RecipeUtilitiesClient
from .recipes_client import RecipesClient


class APIClient:
    """
    Main API client combining all endpoint clients.

    This provides organized access to all API endpoints through
    separate client instances for each router/resource group.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url

        # Client instances for each router/resource
        self.health = HealthClient(base_url)
        self.recipe_utilities = RecipeUtilitiesClient(base_url)
        self.recipes = RecipesClient(base_url)

    # Legacy methods for backward compatibility during transition
    # These delegate to the appropriate specialized client

    def extract_recipe(self, input_text: str):
        """Legacy method - use recipe_utilities.extract_recipe instead."""
        return self.recipe_utilities.extract_recipe(input_text)
