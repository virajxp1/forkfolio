from pydantic import BaseModel


class Recipe(BaseModel):
    title: str
    ingredients: list[str]  # Simplified: just strings like "200g pasta", "tomato sauce"
    instructions: list[str]
    servings: str
    cook_time: str
    prep_time: str
