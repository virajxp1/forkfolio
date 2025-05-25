from abc import ABC, abstractmethod


class RecipeInputCleanup(ABC):
    """
    Abstract base class for cleaning up messy recipe input data.

    This service handles the pre-processing step to clean up scraped or
    messy input data before recipe extraction.
    """

    @abstractmethod
    def cleanup_input(self, messy_input: str) -> str:
        """
        Clean up messy input data and return cleaned text.

        Args:
            messy_input: Raw input string that may contain HTML, ads,
                        navigation elements, or other unwanted content

        Returns:
            Cleaned string containing only recipe-related content
        """
        pass
