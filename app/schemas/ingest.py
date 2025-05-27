from pydantic import BaseModel, Field


# Request model for ingestion
class RecipeIngestionRequest(BaseModel):
    """Request model for recipe extraction from raw text."""

    raw_input: str = Field(
        ...,
        description="Raw unstructured recipe input text",
        min_length=10,
        example=(
            "Chocolate Chip Cookies\n\n"
            "Ingredients:\n- 2 cups flour\n- 1 cup butter\n\n"
            "Instructions:\n1. Mix ingredients\n2. Bake at 350°F"
        ),
    )
