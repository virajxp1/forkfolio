from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


# Request model for ingestion
class RecipeIngestionRequest(BaseModel):
    """Request model for recipe extraction from raw text."""

    model_config = ConfigDict(populate_by_name=True)

    raw_input: str = Field(
        ...,
        description="Raw unstructured recipe input text",
        min_length=10,
        json_schema_extra={
            "example": (
                "Chocolate Chip Cookies\n\n"
                "Ingredients:\n- 2 cups flour\n- 1 cup butter\n\n"
                "Instructions:\n1. Mix ingredients\n2. Bake at 350°F"
            )
        },
    )
    source_url: AnyHttpUrl | None = Field(
        None,
        description="Optional source URL where the recipe was sourced from.",
        alias="sourceUrl",
        json_schema_extra={"example": "https://example.com/chocolate-chip-cookies"},
    )
    enforce_deduplication: bool = Field(
        True,
        description=(
            "When true, attempt to detect and return duplicates instead of inserting."
        ),
        json_schema_extra={"example": True},
    )
    is_test: bool = Field(
        False,
        description="Mark the resulting recipe as test data.",
        alias="isTest",
    )
    is_public: bool = Field(
        True,
        description="Whether the saved recipe is public or private.",
        alias="isPublic",
    )
    created_by_user_id: UUID | None = Field(
        None,
        description="User id that created the recipe.",
        alias="createdByUserId",
    )


class RecipeUrlPreviewRequest(BaseModel):
    """Request model for recipe preview extraction from a source URL."""

    model_config = ConfigDict(populate_by_name=True)

    url: AnyHttpUrl = Field(
        ...,
        description="Recipe page URL to fetch and parse for preview extraction.",
        json_schema_extra={"example": "https://example.com/chocolate-chip-cookies"},
    )
