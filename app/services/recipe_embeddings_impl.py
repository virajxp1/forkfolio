from app.core.logging import get_logger
from app.services.data.managers.recipe_manager import RecipeManager
from app.services.llm_generation_service import make_embedding
from app.services.recipe_embeddings import RecipeEmbeddingsService

logger = get_logger(__name__)


class RecipeEmbeddingsServiceImpl(RecipeEmbeddingsService):
    """Generate and store embeddings for recipes."""

    def __init__(self, recipe_manager: RecipeManager = None):
        self.recipe_manager = recipe_manager or RecipeManager()

    def embed_title_ingredients(
        self, recipe_id: str, title: str, ingredients: list[str]
    ) -> None:
        embedding_text = self._build_title_ingredients_text(title, ingredients)
        embedding = make_embedding(embedding_text)
        self.recipe_manager.create_recipe_embedding(
            recipe_id=recipe_id,
            embedding_type="title_ingredients",
            embedding=embedding,
        )
        logger.info(f"Stored embedding for recipe {recipe_id}")

    @staticmethod
    def _build_title_ingredients_text(title: str, ingredients: list[str]) -> str:
        ingredients_text = ", ".join(ingredients)
        return f"Title: {title}\nIngredients: {ingredients_text}"
