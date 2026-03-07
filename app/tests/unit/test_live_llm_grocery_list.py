"""
Unit test for live LLM grocery list aggregation.
"""

import pytest

from app.core.config import settings
from app.services.grocery_list_aggregation_impl import GroceryListAggregationServiceImpl
from app.tests.utils.helpers import maybe_throttle


@pytest.mark.slow
def test_live_grocery_list_aggregation_returns_merged_items() -> None:
    if not settings.OPEN_ROUTER_API_KEY:
        pytest.skip("OPEN_ROUTER_API_KEY not set; skipping live LLM test.")

    service = GroceryListAggregationServiceImpl()
    ingredients = [
        "1 tomato",
        "2 tomatoes",
        "1 onion",
        "1 red onion",
        "2 cloves garlic",
    ]

    maybe_throttle()
    grocery_items, error = service.aggregate_ingredients(ingredients)

    assert error is None
    assert grocery_items is not None
    assert isinstance(grocery_items, list)
    assert grocery_items
    assert any("tomato" in item.lower() for item in grocery_items)
    assert any("onion" in item.lower() for item in grocery_items)
