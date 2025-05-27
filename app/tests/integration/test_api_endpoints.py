"""
Integration tests for API endpoints.
Tests API layer with mocked services - faster than E2E tests.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from app.main import app
from app.schemas.recipe import Recipe


class TestRecipeAPI:
    """Integration tests for recipe API endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = self.client.get("/api/v1/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch('app.services.recipe_extractor_impl.RecipeExtractorImpl.extract_recipe_from_raw_text')
    def test_ingest_recipe_success(self, mock_extract):
        """Test successful recipe ingestion."""
        # Arrange
        mock_recipe = Recipe(
            title="API Test Recipe",
            ingredients=["1 cup flour", "2 eggs"],
            instructions=["Mix", "Bake"],
            servings="4",
            total_time="30 minutes"
        )
        mock_extract.return_value = (mock_recipe, None)

        # Act
        response = self.client.post(
            "/api/v1/ingest-raw-recipe",
            json={"raw_input": "Test recipe content"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "API Test Recipe"
        assert len(data["ingredients"]) == 2
        assert len(data["instructions"]) == 2
        mock_extract.assert_called_once_with("Test recipe content")

    @patch('app.services.recipe_extractor_impl.RecipeExtractorImpl.extract_recipe_from_raw_text')
    def test_ingest_recipe_service_error(self, mock_extract):
        """Test handling of service errors."""
        # Arrange
        mock_extract.return_value = (None, "Service temporarily unavailable")

        # Act
        response = self.client.post(
            "/api/v1/ingest-raw-recipe",
            json={"raw_input": "Test recipe content"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Service temporarily unavailable" in data["error"]

    def test_ingest_recipe_validation_error(self):
        """Test request validation."""
        # Act - missing required field
        response = self.client.post(
            "/api/v1/ingest-raw-recipe",
            json={}
        )

        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_ingest_recipe_empty_input(self):
        """Test empty input validation."""
        # Act
        response = self.client.post(
            "/api/v1/ingest-raw-recipe",
            json={"raw_input": ""}
        )

        # Assert
        assert response.status_code == 422
