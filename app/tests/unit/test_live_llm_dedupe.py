"""
Unit test for live LLM deduplication adjudication.
"""

import pytest

from app.api.schemas import Recipe
from app.core.config import settings
from app.core.prompts import DEDUPLICATION_SYSTEM_PROMPT
from app.services.llm_generation_service import make_llm_call_structured_output_generic
from app.services.recipe_dedupe_impl import DedupeDecision, RecipeDedupeServiceImpl
from app.tests.utils.helpers import maybe_throttle


@pytest.mark.slow
def test_dedupe_llm_classifies_duplicate() -> None:
    if not settings.OPEN_ROUTER_API_KEY:
        pytest.skip("OPEN_ROUTER_API_KEY not set; skipping live LLM test.")

    recipe = Recipe(
        title="Zesty Lime Pasta",
        servings="2",
        total_time="15 minutes",
        ingredients=[
            "200g pasta",
            "1 tbsp olive oil",
            "1 tbsp lime juice",
            "1 tsp lime zest",
            "1/4 tsp salt",
        ],
        instructions=[
            "Boil pasta.",
            "Toss with oil, lime juice, zest, and salt.",
        ],
    )
    existing_recipe = {
        "title": "Zesty Lime Pasta",
        "ingredients": [
            "200g pasta",
            "1 tbsp olive oil",
            "1 tbsp lime juice",
            "1 tsp lime zest",
            "1/4 tsp salt",
        ],
        "instructions": [
            "Boil pasta.",
            "Toss with oil, lime juice, zest, and salt.",
        ],
    }

    user_prompt = RecipeDedupeServiceImpl._build_user_prompt(recipe, existing_recipe)
    decision, error = make_llm_call_structured_output_generic(
        user_prompt=user_prompt,
        system_prompt=DEDUPLICATION_SYSTEM_PROMPT,
        model_class=DedupeDecision,
        schema_name="dedupe_decision",
    )

    assert error is None
    assert decision is not None
    assert decision.decision == "duplicate"
    assert decision.reason
    maybe_throttle()
