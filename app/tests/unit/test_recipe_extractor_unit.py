"""
Unit tests for RecipeExtractorImpl.
Tests business logic in isolation without external dependencies.
"""
import pytest
from unittest.mock import Mock, patch, ANY
from app.services.recipe_extractor_impl import RecipeExtractorImpl
from app.schemas.recipe import Recipe


class TestRecipeExtractorImpl:
    """Unit tests for RecipeExtractorImpl business logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = RecipeExtractorImpl()

    def test_extract_recipe_empty_input(self):
        """Test that empty input returns appropriate error."""
        recipe, error = self.extractor.extract_recipe_from_raw_text("")

        assert recipe is None
        assert error == "Input text is empty or contains only whitespace"

    def test_extract_recipe_whitespace_input(self):
        """Test that whitespace-only input returns appropriate error."""
        recipe, error = self.extractor.extract_recipe_from_raw_text("   \n\t   ")

        assert recipe is None
        assert error == "Input text is empty or contains only whitespace"

    @patch('app.services.recipe_extractor_impl.make_llm_call_structured_output_generic')
    def test_extract_recipe_success(self, mock_llm_call):
        """Test successful recipe extraction."""
        # Arrange
        mock_recipe = Recipe(
            title="Test Recipe",
            ingredients=["1 cup flour", "2 eggs"],
            instructions=["Mix ingredients", "Bake"],
            servings="4",
            total_time="30 minutes"
        )
        mock_llm_call.return_value = (mock_recipe, None)

        # Act
        recipe, error = self.extractor.extract_recipe_from_raw_text("Test recipe text")

        # Assert
        assert recipe == mock_recipe
        assert error is None
        mock_llm_call.assert_called_once_with(
            user_prompt="Test recipe text",
            system_prompt=ANY,  # We don't care about exact prompt content
            model_class=Recipe,
            schema_name="recipe_extraction"
        )

    @patch('app.services.recipe_extractor_impl.make_llm_call_structured_output_generic')
    def test_extract_recipe_llm_error(self, mock_llm_call):
        """Test handling of LLM service errors."""
        # Arrange
        mock_llm_call.return_value = (None, "LLM service unavailable")

        # Act
        recipe, error = self.extractor.extract_recipe_from_raw_text("Test recipe text")

        # Assert
        assert recipe is None
        assert error == "LLM service unavailable"

    @patch('app.services.recipe_extractor_impl.make_llm_call_structured_output_generic')
    def test_extract_recipe_calls_llm_with_correct_parameters(self, mock_llm_call):
        """Test that LLM is called with correct parameters."""
        # Arrange
        mock_llm_call.return_value = (None, "Some error")
        input_text = "Complex recipe with multiple steps"

        # Act
        self.extractor.extract_recipe_from_raw_text(input_text)

        # Assert
        mock_llm_call.assert_called_once()
        call_args = mock_llm_call.call_args
        assert call_args[1]['user_prompt'] == input_text
        assert call_args[1]['model_class'] == Recipe
        assert call_args[1]['schema_name'] == "recipe_extraction"
