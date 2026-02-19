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
from app.services.recipe_dedupe import RecipeDedupeService
from app.services.recipe_dedupe_impl import RecipeDedupeServiceImpl

logger = get_logger(__name__)


class RecipeProcessingService:
    """
    Service that handles the complete recipe processing pipeline:
    1. Cleanup raw input
    2. Extract structured recipe data
    3. Deduplicate
    4. Generate embeddings
    5. Store in database (recipe + embeddings)
    6. Return database ID
    """

    def __init__(
        self,
        cleanup_service: RecipeInputCleanup = None,
        extractor_service: RecipeExtractorService = None,
        recipe_manager: RecipeManager = None,
        embeddings_service: RecipeEmbeddingsService = None,
        dedupe_service: RecipeDedupeService = None,
    ):
        self.cleanup_service = cleanup_service or RecipeInputCleanupServiceImpl()
        self.extractor_service = extractor_service or RecipeExtractorImpl()
        self.recipe_manager = recipe_manager or RecipeManager()
        self.embeddings_service = embeddings_service or RecipeEmbeddingsServiceImpl()
        self.dedupe_service = dedupe_service or RecipeDedupeServiceImpl()

    def process_raw_recipe(
        self,
        raw_input: str,
        source_url: Optional[str] = None,
        enforce_deduplication: bool = True,
        is_test: bool = False,
    ) -> tuple[Optional[str], Optional[str], bool]:
        """
        Process raw recipe input through the complete pipeline.

        Args:
            raw_input: Raw unstructured recipe text
            source_url: Optional source URL for reference
            enforce_deduplication: When true, attempt to dedupe before inserting
            is_test: Mark the resulting recipe as test data

        Returns:
            Tuple of (recipe_id, error_message, created).
            If successful, recipe_id contains the database ID and created indicates
            whether a new recipe was inserted.
        """
        try:
            # Step 1: Clean up the raw input
            cleaned_text = self._cleanup_input(raw_input)
            if not cleaned_text:
                return None, "Failed to cleanup input text", False

            # Step 2: Extract structured recipe data
            recipe, extraction_error = self._extract_recipe(cleaned_text)
            if extraction_error or not recipe:
                return None, f"Recipe extraction failed: {extraction_error}", False

            # Step 3: Deduplicate
            if enforce_deduplication:
                is_duplicate, existing_id = self.dedupe_service.find_duplicate(recipe)
                if is_duplicate and existing_id:
                    logger.info(f"Duplicate recipe detected: {existing_id}")
                    return existing_id, None, False

            # Step 4: Generate embeddings (title + ingredients)
            embedding = self._generate_title_ingredients_embedding(recipe)
            if embedding is None:
                return None, "Failed to generate recipe embeddings", False

            # Step 5: Insert into database (recipe + embeddings)
            recipe_id = self._store_recipe(recipe, source_url, embedding, is_test)
            if not recipe_id:
                return None, "Failed to store recipe in database", False
            logger.info(f"Successfully processed recipe with ID: {recipe_id}")
            return recipe_id, None, True

        except Exception as e:
            error_msg = f"Recipe processing failed: {e!s}"
            logger.error(error_msg)
            return None, error_msg, False

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
