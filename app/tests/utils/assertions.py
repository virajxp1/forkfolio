"""Simple test assertions."""


def assert_recipe_has_content(recipe_data: dict, allow_empty: bool = False) -> None:
    """Assert that a recipe has meaningful content."""
    if allow_empty:
        return

    has_content = (
        recipe_data.get("title", "").strip()
        or len(recipe_data.get("ingredients", [])) > 0
    )
    assert has_content, (
        f"Recipe should have title or ingredients but got: "
        f"title='{recipe_data.get('title')}', "
        f"ingredients={recipe_data.get('ingredients')}"
    )
