from app.api.schemas import Recipe
from app.services import recipe_extractor_impl
from app.services.recipe_extractor_impl import RecipeExtractorImpl


def test_extract_recipe_backfills_missing_title_and_instructions(monkeypatch) -> None:
    raw_text = (
        "Simple Omelet\n"
        "Servings: 1\n"
        "Total time: 10 minutes\n"
        "Ingredients:\n- 2 eggs\n- 1 tbsp butter\n- Salt\n"
        "Instructions:\n1. Beat eggs.\n2. Melt butter.\n3. Cook eggs.\n"
    )

    def fake_llm_call(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return (
            Recipe(
                title="",
                ingredients=["2 eggs", "1 tbsp butter", "Salt"],
                instructions=[],
                servings="",
                total_time="",
            ),
            None,
        )

    monkeypatch.setattr(
        recipe_extractor_impl,
        "make_llm_call_structured_output_generic",
        fake_llm_call,
    )

    recipe, error = RecipeExtractorImpl().extract_recipe_from_raw_text(raw_text)

    assert error is None
    assert recipe is not None
    assert recipe.title == "Simple Omelet"
    assert recipe.instructions == ["Beat eggs.", "Melt butter.", "Cook eggs."]
    assert recipe.ingredients == ["2 eggs", "1 tbsp butter", "Salt"]


def test_extract_recipe_backfills_missing_ingredients(monkeypatch) -> None:
    raw_text = (
        "Simple Omelet\n"
        "Servings: 1\n"
        "Total time: 10 minutes\n"
        "Ingredients:\n- 2 eggs\n- 1 tbsp butter\n- Salt\n"
        "Instructions:\n1. Beat eggs.\n2. Melt butter.\n3. Cook eggs.\n"
    )

    def fake_llm_call(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return (
            Recipe(
                title="Simple Omelet",
                ingredients=[],
                instructions=["Beat eggs.", "Melt butter.", "Cook eggs."],
                servings="",
                total_time="",
            ),
            None,
        )

    monkeypatch.setattr(
        recipe_extractor_impl,
        "make_llm_call_structured_output_generic",
        fake_llm_call,
    )

    recipe, error = RecipeExtractorImpl().extract_recipe_from_raw_text(raw_text)

    assert error is None
    assert recipe is not None
    assert recipe.ingredients == ["2 eggs", "1 tbsp butter", "Salt"]


def test_extract_recipe_uses_deterministic_fallback_on_llm_failure(monkeypatch) -> None:
    raw_text = (
        "Simple Pasta\n"
        "Ingredients:\n- 200g pasta\n- 1 cup tomato sauce\n"
        "Instructions:\n1. Boil pasta\n2. Add sauce\n"
    )

    def fake_llm_call(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return None, "Model returned no JSON content. finish_reason=stop"

    monkeypatch.setattr(
        recipe_extractor_impl,
        "make_llm_call_structured_output_generic",
        fake_llm_call,
    )

    recipe, error = RecipeExtractorImpl().extract_recipe_from_raw_text(raw_text)

    assert error is None
    assert recipe is not None
    assert recipe.title == "Simple Pasta"
    assert recipe.ingredients == ["200g pasta", "1 cup tomato sauce"]
    assert recipe.instructions == ["Boil pasta", "Add sauce"]


def test_extract_recipe_keeps_error_when_fallback_has_no_recipe_sections(
    monkeypatch,
) -> None:
    raw_text = "This is not a recipe."

    def fake_llm_call(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return None, "Model returned no JSON content. finish_reason=stop"

    monkeypatch.setattr(
        recipe_extractor_impl,
        "make_llm_call_structured_output_generic",
        fake_llm_call,
    )

    recipe, error = RecipeExtractorImpl().extract_recipe_from_raw_text(raw_text)

    assert recipe is None
    assert error == "Model returned no JSON content. finish_reason=stop"


def test_extract_recipe_calls_llm_when_structured_input_has_no_title(
    monkeypatch,
) -> None:
    raw_text = (
        "Ingredients:\n- 2 eggs\n- 1 tbsp butter\n"
        "Instructions:\n1. Beat eggs.\n2. Cook eggs.\n"
    )
    calls = {"count": 0}

    def fake_llm_call(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        calls["count"] += 1
        return (
            Recipe(
                title="Generated Omelet",
                ingredients=["2 eggs", "1 tbsp butter"],
                instructions=["Beat eggs.", "Cook eggs."],
                servings="1",
                total_time="8 minutes",
            ),
            None,
        )

    monkeypatch.setattr(
        recipe_extractor_impl,
        "make_llm_call_structured_output_generic",
        fake_llm_call,
    )

    recipe, error = RecipeExtractorImpl().extract_recipe_from_raw_text(raw_text)

    assert error is None
    assert recipe is not None
    assert calls["count"] == 1
    assert recipe.title == "Generated Omelet"


def test_extract_recipe_fallback_ignores_metadata_lines_in_ingredients(
    monkeypatch,
) -> None:
    raw_text = (
        "Simple Soup\n"
        "Ingredients:\n- 1 cup water\nServings: 2\nTotal time: 10 minutes\n- Salt\n"
        "Instructions:\n1. Boil water.\n2. Add salt.\n"
    )

    def fake_llm_call(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return None, "Model returned no JSON content. finish_reason=stop"

    monkeypatch.setattr(
        recipe_extractor_impl,
        "make_llm_call_structured_output_generic",
        fake_llm_call,
    )

    recipe, error = RecipeExtractorImpl().extract_recipe_from_raw_text(raw_text)

    assert error is None
    assert recipe is not None
    assert recipe.title == "Simple Soup"
    assert recipe.ingredients == ["1 cup water", "Salt"]
    assert recipe.servings == "2"
    assert recipe.total_time == "10 minutes"


def test_extract_recipe_fallback_ignores_numbered_ingredients_for_instructions(
    monkeypatch,
) -> None:
    raw_text = (
        "Simple Pasta\n"
        "Ingredients:\n1. 200g pasta\n2. 1 cup tomato sauce\n"
        "Instructions:\n1. Boil pasta\n2. Add sauce\n"
    )

    def fake_llm_call(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        raise AssertionError("deterministic fallback should bypass LLM call")

    monkeypatch.setattr(
        recipe_extractor_impl,
        "make_llm_call_structured_output_generic",
        fake_llm_call,
    )

    recipe, error = RecipeExtractorImpl().extract_recipe_from_raw_text(raw_text)

    assert error is None
    assert recipe is not None
    assert recipe.title == "Simple Pasta"
    assert recipe.ingredients == ["200g pasta", "1 cup tomato sauce"]
    assert recipe.instructions == ["Boil pasta", "Add sauce"]
