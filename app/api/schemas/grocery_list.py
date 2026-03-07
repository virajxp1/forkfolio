from uuid import UUID

from pydantic import BaseModel, Field


class GroceryListCreateRequest(BaseModel):
    """Request model for generating an aggregated grocery list."""

    recipe_ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Recipe IDs selected by the user for grocery list generation.",
        json_schema_extra={
            "example": [
                "11111111-1111-1111-1111-111111111111",
                "22222222-2222-2222-2222-222222222222",
            ]
        },
    )
