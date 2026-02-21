from app.core.logging import get_logger
from app.services.llm_generation_service import make_embedding
from app.services.recipe_embeddings import RecipeEmbeddingsService

logger = get_logger(__name__)


class RecipeEmbeddingsServiceImpl(RecipeEmbeddingsService):
    """Generate embeddings for recipes."""

    def embed_title_ingredients(
        self, title: str, ingredients: list[str]
    ) -> list[float]:
        embedding_text = self._build_title_ingredients_text(title, ingredients)
        embedding = make_embedding(embedding_text)
        logger.info("Generated embedding for recipe title + ingredients")
        return embedding

    def embed_search_query(self, query: str) -> list[float]:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Search query cannot be empty.")
        embedding_text = self._build_title_ingredients_text(
            title=normalized_query,
            ingredients=[],
        )
        embedding = make_embedding(embedding_text)
        logger.info("Generated embedding for semantic recipe search query")
        return embedding

    @staticmethod
    def _build_title_ingredients_text(title: str, ingredients: list[str]) -> str:
        ingredients_text = ", ".join(ingredients)
        return f"Title: {title}\nIngredients: {ingredients_text}"
