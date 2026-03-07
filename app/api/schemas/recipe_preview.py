from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class RecipeUrlPreviewRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    start_url: HttpUrl = Field(
        ...,
        description="Recipe page URL to scrape.",
    )
    target_instruction: str = Field(
        ...,
        alias="target_prompt",
        description="Instruction passed to the scraper.",
        min_length=5,
    )
    max_steps: int = Field(
        5,
        ge=1,
        le=50,
        description="Max browsing steps.",
    )
    max_actions_per_step: int = Field(
        1,
        ge=1,
        le=4,
        description="Max actions per step.",
    )
