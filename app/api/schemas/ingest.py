from pydantic import BaseModel, ConfigDict, Field


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

    is_test: bool = Field(
        False,
        description="Mark the resulting recipe as test data.",
        alias="isTest",
    )
