"""E2E coverage for cursor pagination on recipe listing."""

from app.tests.clients.api_client import APIClient
from app.tests.utils.constants import HTTP_OK


def test_list_recipes_paginates_with_unique_ids(api_client: APIClient) -> None:
    paged_recipe_ids: list[str] = []
    seen_cursors: set[str] = set()
    cursor: str | None = None

    for page_index in range(5):
        list_response = api_client.recipes.list_recipes(limit=1, cursor=cursor)
        assert list_response["status_code"] == HTTP_OK
        list_data = list_response["data"]
        assert list_data.get("success") is True

        recipes = list_data.get("recipes")
        assert isinstance(recipes, list)
        assert len(recipes) == 1, "Expected at least 5 recipes to exist in the DB"

        recipe_id = recipes[0].get("id")
        assert isinstance(recipe_id, str)
        paged_recipe_ids.append(recipe_id)

        next_cursor = list_data.get("next_cursor")
        if page_index < 4:
            assert isinstance(next_cursor, str)
            assert next_cursor
            assert next_cursor not in seen_cursors
            seen_cursors.add(next_cursor)
        cursor = next_cursor

    assert len(paged_recipe_ids) == 5
    assert len(set(paged_recipe_ids)) == 5
