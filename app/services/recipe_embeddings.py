from abc import ABC, abstractmethod


class RecipeEmbeddingsService(ABC):
    """Interface for generating recipe embeddings."""

    @abstractmethod
    def embed_title_ingredients(
        self, title: str, ingredients: list[str]
    ) -> list[float]:
        """Generate an embedding for title + ingredients."""
        raise NotImplementedError

    @abstractmethod
    def embed_search_query(self, query: str) -> list[float]:
        """Generate an embedding for semantic recipe search queries."""
        raise NotImplementedError
