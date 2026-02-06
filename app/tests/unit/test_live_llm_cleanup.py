"""
Unit tests for live LLM cleanup service.
"""

import pytest

from app.core.config import settings
from app.services.recipe_input_cleanup_impl import RecipeInputCleanupServiceImpl


@pytest.mark.slow
def test_cleanup_returns_text() -> None:
    if not settings.OPEN_ROUTER_API_KEY:
        pytest.skip("OPEN_ROUTER_API_KEY not set; skipping live LLM test.")

    service = RecipeInputCleanupServiceImpl()
    raw_text = (
        "<html><body><h1>Quick Salad</h1>"
        "<p>Ingredients: 1 tomato, 1 cucumber</p>"
        "<p>Instructions: Chop and toss.</p>"
        "<nav>Home | About</nav></body></html>"
    )

    cleaned = service.cleanup_input(raw_text)
    assert isinstance(cleaned, str)
    assert len(cleaned.strip()) > 0
