from abc import ABC, abstractmethod
from app.schemas.recipe import Recipe


class RecipeExtractorService(ABC):

    @abstractmethod
    def extractRecipeFromRawText(self, text: str) -> Recipe:
        """
        Extract recipe data from raw text
        
        Args:
            text: The raw text containing recipe information
            
        Returns:
            Recipe object containing the extracted recipe information
        """
        pass
