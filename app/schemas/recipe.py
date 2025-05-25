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


# Example request body for API documentation
RAW_RECIPE_BODY = RecipeCleanupRequest(
    raw_text="""
    <html><head><title>Best Chocolate Chip Cookies</title></head>
    <body>
    <nav>Home | Recipes | About</nav>
    <div class="recipe">
    <h1>Best Chocolate Chip Cookies</h1>
    <p>Ingredients:</p>
    <ul>
    <li>2 cups all-purpose flour</li>
    <li>1 cup butter, softened</li>
    <li>3/4 cup brown sugar</li>
    <li>1/2 cup white sugar</li>
    <li>2 eggs</li>
    <li>2 tsp vanilla extract</li>
    <li>1 tsp baking soda</li>
    <li>1 tsp salt</li>
    <li>2 cups chocolate chips</li>
    </ul>
    <p>Instructions:</p>
    <ol>
    <li>Preheat oven to 375°F</li>
    <li>Mix butter and sugars until fluffy</li>
    <li>Add eggs and vanilla</li>
    <li>Combine dry ingredients separately</li>
    <li>Mix wet and dry ingredients</li>
    <li>Fold in chocolate chips</li>
    <li>Bake for 9-11 minutes</li>
    </ol>
    </div>
    <footer>Copyright 2024</footer>
    </body></html>
    """,
    source_url="https://example.com/cookies",
)
