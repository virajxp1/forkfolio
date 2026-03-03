from pydantic import BaseModel, ConfigDict, Field


class RecipeUrlPreviewRequest(BaseModel):
    """
    Request model for previewing recipe content from a URL without saving.
    """

    model_config = ConfigDict(populate_by_name=True)

    start_url: str = Field(
        ...,
        description="Starting URL to scrape for recipe content.",
        min_length=5,
        json_schema_extra={"example": "https://www.example.com/recipes/pasta"},
    )
    target_instruction: str = Field(
        ...,
        alias="target_prompt",
        description=(
            "Instruction passed to the browser agent for what to extract from the URL."
        ),
        min_length=5,
        json_schema_extra={
            "example": (
                "Extract the full recipe text including title, ingredients, "
                "instructions, servings, and total time."
            )
        },
    )
    max_steps: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum browser-agent steps.",
        json_schema_extra={"example": 10},
    )
    max_actions_per_step: int = Field(
        2,
        ge=1,
        le=4,
        description="Maximum actions per browser-agent step.",
        json_schema_extra={"example": 2},
    )
