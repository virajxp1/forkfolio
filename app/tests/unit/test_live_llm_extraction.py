"""
Unit tests for live LLM extraction service.
"""

import pytest

from app.core.config import settings
from app.services.recipe_extractor_impl import RecipeExtractorImpl
from app.tests.utils.helpers import maybe_throttle


@pytest.mark.slow
def test_extract_recipe_from_text() -> None:
    if not settings.OPEN_ROUTER_API_KEY:
        pytest.skip("OPEN_ROUTER_API_KEY not set; skipping live LLM test.")

    service = RecipeExtractorImpl()
    input_text = (
        "Simple Omelet\n"
        "Servings: 1\n"
        "Total time: 10 minutes\n"
        "Ingredients:\n- 2 eggs\n- 1 tbsp butter\n- Salt\n"
        "Instructions:\n1. Beat eggs.\n2. Melt butter.\n3. Cook eggs.\n"
    )

    recipe, error = service.extract_recipe_from_raw_text(input_text)
    assert error is None
    assert recipe is not None
    assert recipe.title
    assert recipe.ingredients
    assert recipe.instructions
    maybe_throttle()
