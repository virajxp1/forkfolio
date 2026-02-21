from abc import ABC, abstractmethod
from typing import Optional

from app.api.schemas import Recipe


class RecipeDedupeService(ABC):
    """Interface for recipe deduplication checks."""

    @abstractmethod
    def find_duplicate(
        self, recipe: Recipe
    ) -> tuple[bool, Optional[str], Optional[list[float]]]:
        """Return (is_duplicate, existing_recipe_id, embedding)."""
        raise NotImplementedError
