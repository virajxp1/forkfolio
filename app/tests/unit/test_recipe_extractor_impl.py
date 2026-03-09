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
