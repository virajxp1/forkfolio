# Sample Recipe for testing
from app.schemas import RecipeCleanupRequest

BRUSCHETTA_RECIPE = """
Bruschetta Recipe
Prep time
5 minutes to 10 minutes

Cook time
2 minutes to 4 minutes

Makes
14 pieces

Ingredients
1 pound tomatoes (3 to 4 medium)
1/4 cup packed fresh basil leaves
1 tablespoon extra-virgin olive oil, plus more for brushing the baguette
1 teaspoon balsamic vinegar
1/2 teaspoon kosher salt
1/4 teaspoon freshly ground black pepper
1/2 (24-inch) baguette
1 clove garlic
Flaky sea salt (optional)
Equipment
Medium bowl
Baking sheet
Serrated knife, chef's knife, and cutting board
Slotted spoon
Measuring cups and spoons
Pastry brush
Instructions
Chop the tomatoes. Core 3 tomatoes and, if they're especially juicy, scoop 
out the seeds (this is optional, but will help prevent the bruschetta from getting 
soggy). 
Chop the tomatoes into 1/2-inch pieces, you'll have about 2 cups. Place in a 
medium bowl.

Make the tomato mixture. Coarsely chop 1/4 cup packed fresh basil leaves and add to 
the bowl with the tomatoes. Add 1 tablespoon extra-virgin olive oil, 1 teaspoon 
balsamic vinegar, 1/2 teaspoon kosher salt, and 1/4 teaspoon freshly ground 
black pepper, and toss to combine. Set aside.

Toast the bread. Arrange a rack in the upper third of the oven (about 5 to 6 inches 
below the broiling element), and heat the broiler to high. Wipe off the cutting 
board and cut half a baguette into 3/4-inch thick slices (you'll have 12 to 14 
slices total). Arrange the baguette slices on a baking sheet and broil, flipping once, 
until golden brown and crisp on both sides, 1 to 2 minutes per side (watch it 
carefully so it doesn't burn).

Rub the toasts with garlic. Peel and halve 1 garlic clove. 
Gently rub the toasts with the cut sides of the garlic.

Brush the toasts with olive oil. Brush each toast with a light coating of olive oil 
(you'll need about 1 to 2 tablespoons).

Top with tomatoes. Taste the tomato mixture and season with more salt and pepper 
as needed. Scoop the tomato mixture out with a slotted spoon and divide evenly 
among the toasts. Sprinkle with flaky salt, if desired, and serve immediately."""


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
