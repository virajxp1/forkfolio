from abc import ABC, abstractmethod


class RecipeEmbeddingsService(ABC):
    """Interface for generating and storing recipe embeddings."""

    @abstractmethod
    def embed_title_ingredients(
        self, recipe_id: str, title: str, ingredients: list[str]
    ) -> None:
        """Generate and store an embedding for title + ingredients."""
        raise NotImplementedError
