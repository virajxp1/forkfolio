import json

from app.services import grocery_list_aggregation_impl
from app.services.grocery_list_aggregation_impl import (
    GroceryListAggregationResult,
    GroceryListAggregationServiceImpl,
)


def test_build_user_prompt_serializes_ingredients() -> None:
    prompt = GroceryListAggregationServiceImpl._build_user_prompt(
        ["2 tomatoes", "1 onion"]
    )
    payload = json.loads(prompt)
    assert payload == {"ingredients": ["2 tomatoes", "1 onion"]}


def test_aggregate_ingredients_returns_empty_for_empty_input() -> None:
    service = GroceryListAggregationServiceImpl()

    ingredients, error = service.aggregate_ingredients([])

    assert error is None
    assert ingredients == []


def test_aggregate_ingredients_returns_llm_output(monkeypatch) -> None:
    service = GroceryListAggregationServiceImpl()

    monkeypatch.setattr(
        grocery_list_aggregation_impl,
        "make_llm_call_structured_output_generic",
        lambda **_kwargs: (
            GroceryListAggregationResult(
                ingredients=["2 tomatoes", " 1 yellow onion ", ""]
            ),
            None,
        ),
    )

    ingredients, error = service.aggregate_ingredients(
        ["1 tomato", "1 tomato", "1 onion"]
    )

    assert error is None
    assert ingredients == ["2 tomatoes", "1 yellow onion"]


def test_aggregate_ingredients_returns_error_when_llm_fails(monkeypatch) -> None:
    service = GroceryListAggregationServiceImpl()

    monkeypatch.setattr(
        grocery_list_aggregation_impl,
        "make_llm_call_structured_output_generic",
        lambda **_kwargs: (None, "llm unavailable"),
    )

    ingredients, error = service.aggregate_ingredients(["1 tomato"])

    assert ingredients is None
    assert error == "llm unavailable"
