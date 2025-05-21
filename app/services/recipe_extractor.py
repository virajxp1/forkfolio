from abc import ABC, abstractmethod

from app.schemas.ingest import RecipeIngestionRequest
from app.schemas.recipe import Recipe


class RecipeExtractorService(ABC):
    @abstractmethod
    def extract_recipe_from_raw_text(
        self, recipe_ingestion_request: RecipeIngestionRequest
    ) -> Recipe:
        """
        Extract recipe data from raw text

        Args:
            text: The raw text containing recipe information

        Returns:
            Recipe object containing the extracted recipe information
            :param recipe_ingestion_request: the input request
        """
        pass
