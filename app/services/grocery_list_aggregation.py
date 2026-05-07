from abc import ABC, abstractmethod
from typing import Optional


class GroceryListAggregationService(ABC):
    """Interface for grocery list aggregation from raw recipe ingredients."""

    @abstractmethod
    def aggregate_ingredients(
        self,
        ingredients: list[str],
    ) -> tuple[Optional[list[str]], Optional[str]]:
        """Return aggregated grocery ingredients or an error message."""
        raise NotImplementedError
