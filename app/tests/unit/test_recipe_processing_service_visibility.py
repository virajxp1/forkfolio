from app.api.schemas import Recipe
from app.services.recipe_processing_service import RecipeProcessingService


class EchoCleanupService:
    def cleanup_input(self, messy_input: str) -> str:
        return messy_input


class StaticRecipeExtractor:
    def extract_recipe_from_raw_text(self, raw_text: str):
        del raw_text
        return (
            Recipe(
                title="Private Pasta",
                ingredients=["200g pasta", "1 cup sauce"],
                instructions=["Boil pasta", "Add sauce"],
                servings="2",
                total_time="20 minutes",
            ),
            None,
        )


class FakeRecipeManager:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_recipe_from_model(
        self,
        recipe: Recipe,
        source_url: str | None = None,
        embedding_type: str | None = None,
        embedding: list[float] | None = None,
        is_test_data: bool = False,
        is_public: bool = True,
        created_by_user_id: str | None = None,
    ) -> str:
        self.calls.append(
            {
                "recipe": recipe,
                "source_url": source_url,
                "embedding_type": embedding_type,
                "embedding": embedding,
                "is_test_data": is_test_data,
                "is_public": is_public,
                "created_by_user_id": created_by_user_id,
            }
        )
        return "11111111-1111-1111-1111-111111111111"


class FakeDedupeService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def find_duplicate(
        self,
        recipe: Recipe,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> tuple[bool, str | None, list[float] | None]:
        self.calls.append(
            {
                "recipe": recipe,
                "include_test_data": include_test_data,
                "viewer_user_id": viewer_user_id,
            }
        )
        return False, None, [0.1, 0.2, 0.3]


def test_process_raw_recipe_scopes_dedupe_to_creator_visibility() -> None:
    recipe_manager = FakeRecipeManager()
    dedupe_service = FakeDedupeService()
    service = RecipeProcessingService(
        cleanup_service=EchoCleanupService(),
        extractor_service=StaticRecipeExtractor(),
        recipe_manager=recipe_manager,
        embeddings_service=object(),
        dedupe_service=dedupe_service,
    )

    recipe_id, error, created = service.process_raw_recipe(
        raw_input="Private Pasta\nIngredients:\n- pasta\nInstructions:\n1. Cook",
        source_url="https://example.com/private-pasta",
        enforce_deduplication=True,
        is_test=False,
        is_public=False,
        created_by_user_id="22222222-2222-2222-2222-222222222222",
    )

    assert error is None
    assert created is True
    assert recipe_id == "11111111-1111-1111-1111-111111111111"
    assert dedupe_service.calls == [
        {
            "recipe": Recipe(
                title="Private Pasta",
                ingredients=["200g pasta", "1 cup sauce"],
                instructions=["Boil pasta", "Add sauce"],
                servings="2",
                total_time="20 minutes",
            ),
            "include_test_data": False,
            "viewer_user_id": "22222222-2222-2222-2222-222222222222",
        }
    ]
    assert recipe_manager.calls == [
        {
            "recipe": Recipe(
                title="Private Pasta",
                ingredients=["200g pasta", "1 cup sauce"],
                instructions=["Boil pasta", "Add sauce"],
                servings="2",
                total_time="20 minutes",
            ),
            "source_url": "https://example.com/private-pasta",
            "embedding_type": "title_ingredients",
            "embedding": [0.1, 0.2, 0.3],
            "is_test_data": False,
            "is_public": False,
            "created_by_user_id": "22222222-2222-2222-2222-222222222222",
        }
    ]
