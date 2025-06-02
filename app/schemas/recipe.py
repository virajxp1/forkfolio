from typing import Optional

from pydantic import BaseModel


class Recipe(BaseModel):
    title: str
    ingredients: list[str]
    instructions: list[str]
    servings: str
    total_time: str

class RecipeCleanupRequest(BaseModel):
    """Request model for cleaning up raw recipe data that needs preprocessing."""

    raw_text: str  # Raw messy input that may contain HTML, ads, etc.
    source_url: Optional[str] = None  # Optional source URL for reference


class RecipeCleanupResponse(BaseModel):
    """Response model for the recipe cleanup endpoint."""

    cleaned_text: str  # The cleaned recipe text from LLM processing
    source_url: Optional[str] = None  # Optional source URL for reference
    original_length: int  # Character count of the original raw input
    cleaned_length: int  # Character count of the cleaned output
