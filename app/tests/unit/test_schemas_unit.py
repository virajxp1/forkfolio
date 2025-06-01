"""
Unit tests for Pydantic schemas/models.
Tests data validation and serialization.
"""

import pytest
from pydantic import ValidationError

from app.schemas.ingest import RecipeIngestionRequest
from app.schemas.recipe import Recipe

# Constants
EXPECTED_INGREDIENT_COUNT = 2
EXPECTED_INSTRUCTION_COUNT = 2


class TestRecipeSchema:
    """Unit tests for Recipe schema."""

    def test_recipe_creation_valid_data(self):
        """Test recipe creation with valid data."""
        recipe = Recipe(
            title="Test Recipe",
            ingredients=["1 cup flour", "2 eggs"],
            instructions=["Mix ingredients", "Bake at 350°F"],
            servings="4 servings",
            total_time="30 minutes",
        )

        assert recipe.title == "Test Recipe"
        assert len(recipe.ingredients) == EXPECTED_INGREDIENT_COUNT
        assert len(recipe.instructions) == EXPECTED_INSTRUCTION_COUNT
        assert recipe.servings == "4 servings"
        assert recipe.total_time == "30 minutes"

    def test_recipe_creation_minimal_data(self):
        """Test recipe creation with minimal required data."""
        recipe = Recipe(
            title="Minimal Recipe",
            ingredients=["flour"],
            instructions=["mix"],
            servings="Not specified",
            total_time="Not specified",
        )

        assert recipe.title == "Minimal Recipe"
        assert recipe.ingredients == ["flour"]
        assert recipe.instructions == ["mix"]

    def test_recipe_validation_missing_title(self):
        """Test validation fails with missing title."""
        with pytest.raises(ValidationError) as exc_info:
            Recipe(
                ingredients=["flour"],
                instructions=["mix"],
                servings="4",
                total_time="30 minutes",
                # Missing title
            )

        assert "title" in str(exc_info.value)

    def test_recipe_validation_missing_ingredients(self):
        """Test validation fails with missing ingredients."""
        with pytest.raises(ValidationError) as exc_info:
            Recipe(
                title="Test Recipe",
                instructions=["mix"],
                servings="4",
                total_time="30 minutes",
                # Missing ingredients
            )

        assert "ingredients" in str(exc_info.value)

    def test_recipe_validation_wrong_type_ingredients(self):
        """Test validation fails with wrong type for ingredients."""
        with pytest.raises(ValidationError) as exc_info:
            Recipe(
                title="Test Recipe",
                ingredients="flour, eggs",  # Should be list, not string
                instructions=["mix"],
                servings="4",
                total_time="30 minutes",
            )

        assert "ingredients" in str(exc_info.value)

    def test_recipe_serialization(self):
        """Test recipe can be serialized to dict."""
        recipe = Recipe(
            title="Test Recipe",
            ingredients=["flour", "eggs"],
            instructions=["mix", "bake"],
            servings="4",
            total_time="30 minutes",
        )

        recipe_dict = recipe.model_dump()

        assert recipe_dict["title"] == "Test Recipe"
        assert recipe_dict["ingredients"] == ["flour", "eggs"]
        assert recipe_dict["instructions"] == ["mix", "bake"]
        assert recipe_dict["servings"] == "4"
        assert recipe_dict["total_time"] == "30 minutes"


class TestRecipeIngestionRequestSchema:
    """Unit tests for RecipeIngestionRequest schema."""

    def test_ingestion_request_valid_data(self):
        """Test ingestion request with valid data."""
        request = RecipeIngestionRequest(
            raw_input="Test recipe content with enough characters"
        )

        assert request.raw_input == "Test recipe content with enough characters"

    def test_ingestion_request_validation_missing_raw_input(self):
        """Test validation fails with missing raw_input."""
        with pytest.raises(ValidationError) as exc_info:
            RecipeIngestionRequest()

        assert "raw_input" in str(exc_info.value)

    def test_ingestion_request_validation_too_short(self):
        """Test validation fails with input too short."""
        with pytest.raises(ValidationError) as exc_info:
            RecipeIngestionRequest(raw_input="short")

        assert "at least 10 characters" in str(exc_info.value)

    def test_ingestion_request_validation_minimum_length(self):
        """Test validation passes with minimum length."""
        request = RecipeIngestionRequest(raw_input="1234567890")  # Exactly 10 chars
        assert request.raw_input == "1234567890"
