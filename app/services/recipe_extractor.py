from abc import ABC, abstractmethod
from typing import Optional, Tuple

from app.schemas.recipe import Recipe


class RecipeExtractorService(ABC):
    """Abstract service for extracting structured recipe data from raw text."""

    @abstractmethod
    def extract_recipe_from_raw_text(
        self, raw_text: str
    ) -> Tuple[Optional[Recipe], Optional[str]]:
        """
        Extract recipe data from raw text input.

        Args:
            raw_text: The unstructured recipe text to process

        Returns:
            A tuple of (recipe, error_message). If successful, recipe contains the Recipe object
            and error_message is None. If failed, recipe is None and error_message contains the error.
        """
        pass
