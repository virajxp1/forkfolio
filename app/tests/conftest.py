"""
Pytest configuration and shared fixtures.
This file is automatically loaded by pytest and provides shared test utilities.
"""

import asyncio
import os
import sys
from unittest.mock import Mock

import pytest

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.schemas.recipe import Recipe
from app.services.recipe_extractor_impl import RecipeExtractorImpl


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_recipe() -> Recipe:
    """Provide a standard mock recipe for testing."""
    return Recipe(
        title="Test Recipe",
        ingredients=["1 cup flour", "2 eggs", "1 tsp salt"],
        instructions=["Mix dry ingredients", "Add wet ingredients", "Bake at 350°F"],
        servings="4 servings",
        total_time="45 minutes",
    )


@pytest.fixture
def recipe_extractor() -> RecipeExtractorImpl:
    """Provide a recipe extractor instance for testing."""
    return RecipeExtractorImpl()


@pytest.fixture
def mock_llm_service():
    """Provide a mock LLM service for unit testing."""
    return Mock()


# Test markers for different test types
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line(
        "markers", "integration: Integration tests (slower, with dependencies)"
    )
    config.addinivalue_line("markers", "e2e: End-to-end tests (slowest, full system)")
    config.addinivalue_line(
        "markers", "slow: Slow tests that can be skipped in development"
    )


# Custom test collection rules
def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark unit tests
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Mark integration tests
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Mark e2e tests
        elif "e2e" in str(item.fspath) or "test_recipe_extraction" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow)
