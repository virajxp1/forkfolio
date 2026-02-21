-- Recipe books schema extension for ForkFolio
-- Run in Supabase SQL editor after the base recipe schema is in place.

CREATE TABLE IF NOT EXISTS recipe_books (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT recipe_books_name_not_blank CHECK (length(trim(name)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_recipe_books_name ON recipe_books(name);
CREATE INDEX IF NOT EXISTS idx_recipe_books_created_at ON recipe_books(created_at DESC);

CREATE TABLE IF NOT EXISTS recipe_book_recipes (
    recipe_book_id UUID NOT NULL REFERENCES recipe_books(id) ON DELETE CASCADE,
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (recipe_book_id, recipe_id)
);

CREATE INDEX IF NOT EXISTS idx_recipe_book_recipes_recipe_id
    ON recipe_book_recipes(recipe_id);
