import json
import uuid

from app.services import recipe_search_reranker_impl
from app.services.recipe_search_reranker_impl import RecipeSearchRerankerServiceImpl


def test_build_user_prompt_normalizes_uuid_ids_for_json() -> None:
    recipe_id = uuid.uuid4()
    prompt = RecipeSearchRerankerServiceImpl._build_user_prompt(
        query="pasta",
        candidates=[
            {
                "id": recipe_id,
                "name": "Carbonara",
                "distance": 0.11,
                "ingredients_preview": ["spaghetti", "egg"],
            }
        ],
        max_results=5,
    )
    payload = json.loads(prompt)
    assert payload["candidates"][0]["id"] == str(recipe_id)


def test_rerank_returns_empty_when_llm_errors(monkeypatch) -> None:
    service = RecipeSearchRerankerServiceImpl()

    monkeypatch.setattr(
        recipe_search_reranker_impl,
        "make_llm_call_structured_output_generic",
        lambda **_kwargs: (None, "llm down"),
    )

    ranked = service.rerank(
        query="pasta",
        candidates=[{"id": str(uuid.uuid4()), "name": "Carbonara"}],
        max_results=3,
    )
    assert ranked == []
