from abc import ABC, abstractmethod


class RecipeEmbeddingsService(ABC):
    """Interface for generating recipe embeddings."""

    @abstractmethod
    def embed_title_ingredients(
        self, title: str, ingredients: list[str]
    ) -> list[float]:
        """Generate an embedding for title + ingredients."""
        raise NotImplementedError
