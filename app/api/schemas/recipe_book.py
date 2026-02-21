from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RecipeBookCreateRequest(BaseModel):
    """Request model for creating a recipe book."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(
        ...,
        description="Recipe book name",
        min_length=1,
        max_length=120,
        json_schema_extra={"example": "Italian Recipe Book"},
    )
    description: Optional[str] = Field(
        None,
        description="Optional recipe book description",
        max_length=1000,
        json_schema_extra={"example": "My favorite pasta and risotto recipes"},
    )
