from typing import Optional

from app.core.logging import get_logger
from app.api.schemas import Recipe
from app.services.recipe_input_cleanup import RecipeInputCleanup
from app.services.recipe_extractor import RecipeExtractorService
from app.services.data.managers.recipe_manager import RecipeManager
from app.services.recipe_extractor_impl import RecipeExtractorImpl
from app.services.recipe_input_cleanup_impl import RecipeInputCleanupServiceImpl
from app.services.recipe_embeddings import RecipeEmbeddingsService
from app.services.recipe_embeddings_impl import RecipeEmbeddingsServiceImpl

logger = get_logger(__name__)


class RecipeProcessingService:
    """
    Service that handles the complete recipe processing pipeline:
    1. Cleanup raw input
    2. Extract structured recipe data
    3. Generate embeddings
    4. Store in database (recipe + embeddings)
    5. Return database ID
    """

    def __init__(
        self,
        cleanup_service: RecipeInputCleanup = None,
        extractor_service: RecipeExtractorService = None,
        recipe_manager: RecipeManager = None,
        embeddings_service: RecipeEmbeddingsService = None,
    ):
        self.cleanup_service = cleanup_service or RecipeInputCleanupServiceImpl()
        self.extractor_service = extractor_service or RecipeExtractorImpl()
        self.recipe_manager = recipe_manager or RecipeManager()
        self.embeddings_service = embeddings_service or RecipeEmbeddingsServiceImpl()

    def process_raw_recipe(
        self,
        raw_input: str,
        source_url: Optional[str] = None,
        is_test: bool = False,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Process raw recipe input through the complete pipeline.

        Args:
            raw_input: Raw unstructured recipe text
            source_url: Optional source URL for reference
            is_test: Mark the resulting recipe as test data

        Returns:
            Tuple of (recipe_id, error_message). If successful, recipe_id contains
            the database ID and error_message is None. If failed, recipe_id is None
            and error_message contains the error.
        """
        try:
            # Step 1: Clean up the raw input
            cleaned_text = self._cleanup_input(raw_input)
            if not cleaned_text:
                return None, "Failed to cleanup input text"

            # Step 2: Extract structured recipe data
            recipe, extraction_error = self._extract_recipe(cleaned_text)
            if extraction_error or not recipe:
                return None, f"Recipe extraction failed: {extraction_error}"

            # Step 3: Generate embeddings (title + ingredients)
            embedding = self._generate_title_ingredients_embedding(recipe)
            if embedding is None:
                return None, "Failed to generate recipe embeddings"

            # Step 4: Insert into database (recipe + embeddings)
            recipe_id = self._store_recipe(recipe, source_url, embedding, is_test)
            if not recipe_id:
                return None, "Failed to store recipe in database"

            logger.info(f"Successfully processed recipe with ID: {recipe_id}")
            return recipe_id, None

        except Exception as e:
            error_msg = f"Recipe processing failed: {e!s}"
            logger.error(error_msg)
            return None, error_msg

    def _cleanup_input(self, raw_input: str) -> Optional[str]:
        """
        Step 1: Clean up messy raw input using the cleanup service.

        Args:
            raw_input: Raw messy input text

        Returns:
            Cleaned text or None if cleanup failed
        """
        try:
            cleaned_text = self.cleanup_service.cleanup_input(raw_input)
            logger.info(
                f"Input cleanup completed. Original length: {len(raw_input)}, "
                f"Cleaned length: {len(cleaned_text)}"
            )
            return cleaned_text
        except Exception as e:
            logger.error(f"Input cleanup failed: {e}")
            return None

    def _extract_recipe(
        self, cleaned_text: str
    ) -> tuple[Optional[Recipe], Optional[str]]:
        """
        Step 2: Extract structured recipe data from cleaned text.

        Args:
            cleaned_text: Clean recipe text

        Returns:
            Tuple of (Recipe object, error_message)
        """
        try:
            recipe, error = self.extractor_service.extract_recipe_from_raw_text(
                cleaned_text
            )
            if error:
                logger.error(f"Recipe extraction failed: {error}")
                return None, error

            logger.info(f"Recipe extraction successful: {recipe.title}")
            return recipe, None

        except Exception as e:
            error_msg = f"Recipe extraction error: {e!s}"
            logger.error(error_msg)
            return None, error_msg

    def _store_recipe(
        self,
        recipe: Recipe,
        source_url: Optional[str],
        embedding: list[float],
        is_test: bool,
    ) -> Optional[str]:
        """
        Step 4: Store the recipe and embeddings in the database.

        Args:
            recipe: Recipe object to store
            source_url: Optional source URL
            embedding: Embedding vector for title + ingredients

        Returns:
            Database ID of stored recipe or None if storage failed
        """
        try:
            # Create the main recipe record and embeddings in one transaction
            recipe_id = self.recipe_manager.create_recipe_from_model(
                recipe=recipe,
                source_url=source_url,
                embedding_type="title_ingredients",
                embedding=embedding,
                is_test_data=is_test,
            )

            logger.info(f"Recipe stored successfully with ID: {recipe_id}")
            return recipe_id

        except Exception as e:
            logger.error(f"Recipe storage failed: {e}")
            return None

    def _generate_title_ingredients_embedding(
        self, recipe: Recipe
    ) -> Optional[list[float]]:
        """Step 3: Generate embeddings for the recipe."""
        try:
            return self.embeddings_service.embed_title_ingredients(
                title=recipe.title,
                ingredients=recipe.ingredients,
            )
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None
