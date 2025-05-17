from typing import Optional

from pydantic import BaseModel


class Ingredient(BaseModel):
    name: str  # e.g., "basil leaves"
    quantity: Optional[str] = None  # e.g., "1/4"
    unit: Optional[str] = None  # e.g., "cup"
    notes: Optional[str] = None  # e.g., "packed", "optional"


class Recipe(BaseModel):
    title: str
    ingredients: list[Ingredient]
    instructions: list[str]
    servings: Optional[str] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    total_time: Optional[str] = None
    tags: Optional[list[str]] = None
    nutrition: Optional[dict[str, str]] = None
    source_url: Optional[str] = None
