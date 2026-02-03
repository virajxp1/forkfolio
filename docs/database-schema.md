# Database Schema Documentation

This document provides a comprehensive overview of the ForkFolio database schema, including table structures, relationships, and SQL commands for table creation.

## Overview

The ForkFolio database uses **PostgreSQL** (via Supabase) with a relational schema designed to store recipes, their ingredients, and cooking instructions. The schema supports:

- **Recipe Management**: Core recipe metadata and information
- **Ordered Ingredients**: Preserved ingredient order for each recipe
- **Step-by-Step Instructions**: Sequential cooking instructions
- **Future Extensibility**: Schema designed for vector embeddings and similarity search

## Table Schemas

### 1. `recipes` (Main Table)

The primary table storing core recipe information and metadata.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, NOT NULL | Unique identifier for each recipe (auto-generated) |
| `title` | VARCHAR | NOT NULL | Recipe title/name |
| `servings` | VARCHAR | NULL | Number of servings (e.g., "4 servings", "6-8 people") |
| `total_time` | VARCHAR | NULL | Total preparation and cooking time (e.g., "30 minutes", "1 hour 15 minutes") |
| `source_url` | VARCHAR | NULL | Optional URL where the recipe was sourced from |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Timestamp when the recipe was created |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Timestamp when the recipe was last updated |

**Indexes:**
- Primary key index on `id`
- Consider adding index on `created_at` for efficient ordering queries

**Relationships:**
- One-to-many with `recipe_ingredients` (CASCADE DELETE)
- One-to-many with `recipe_instructions` (CASCADE DELETE)
- One-to-many with `recipe_embeddings` (CASCADE DELETE, future)

---

### 2. `recipe_ingredients` (Related Table)

Stores the list of ingredients for each recipe with preserved ordering.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, NOT NULL | Unique identifier for each ingredient entry |
| `recipe_id` | UUID | FOREIGN KEY, NOT NULL | References `recipes.id` (ON DELETE CASCADE) |
| `ingredient_text` | TEXT | NOT NULL | Full ingredient description (e.g., "2 cups all-purpose flour", "1 tsp salt") |
| `order_index` | INTEGER | NOT NULL | Zero-based index preserving the order of ingredients in the recipe |

**Indexes:**
- Primary key index on `id`
- Foreign key index on `recipe_id` (automatically created)
- Composite index on `(recipe_id, order_index)` for efficient ordered retrieval

**Relationships:**
- Many-to-one with `recipes` (CASCADE DELETE)

**Constraints:**
- `order_index` should be unique per `recipe_id` (consider adding UNIQUE constraint)

---

### 3. `recipe_instructions` (Related Table)

Stores step-by-step cooking instructions for each recipe.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, NOT NULL | Unique identifier for each instruction entry |
| `recipe_id` | UUID | FOREIGN KEY, NOT NULL | References `recipes.id` (ON DELETE CASCADE) |
| `instruction_text` | TEXT | NOT NULL | Full instruction text for this step |
| `step_number` | INTEGER | NOT NULL | Sequential step number (1-based) |

**Indexes:**
- Primary key index on `id`
- Foreign key index on `recipe_id` (automatically created)
- Composite index on `(recipe_id, step_number)` for efficient ordered retrieval

**Relationships:**
- Many-to-one with `recipes` (CASCADE DELETE)

**Constraints:**
- `step_number` should be unique per `recipe_id` (consider adding UNIQUE constraint)
- `step_number` should be >= 1

---

### 4. `recipe_embeddings` (Future/Planned Table)

Planned table for storing vector embeddings to enable similarity search and ML-based recipe recommendations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, NOT NULL | Unique identifier for each embedding entry |
| `recipe_id` | UUID | FOREIGN KEY, NOT NULL | References `recipes.id` (ON DELETE CASCADE) |
| `embedding_type` | VARCHAR | NOT NULL | Type of embedding (e.g., "ingredient", "instruction", "full_recipe") |
| `embedding` | VECTOR | NULL | Vector representation for ML features (requires pgvector extension) |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Timestamp when the embedding was created |

**Indexes:**
- Primary key index on `id`
- Foreign key index on `recipe_id` (automatically created)
- Vector index on `embedding` (using HNSW or IVFFlat, requires pgvector)

**Relationships:**
- Many-to-one with `recipes` (CASCADE DELETE)

**Note:** This table is not yet implemented in the codebase but is planned for future ML features.

---

## Entity Relationship Diagram

```
┌─────────────────┐
│    recipes      │
├─────────────────┤
│ id (PK)         │◄─────┐
│ title           │      │
│ servings        │      │
│ total_time      │      │
│ source_url      │      │
│ created_at      │      │
│ updated_at      │      │
└─────────────────┘      │
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         │               │               │
┌────────▼────────┐ ┌───▼──────────┐ ┌──▼──────────────┐
│recipe_ingredients│ │recipe_       │ │recipe_          │
│                  │ │instructions  │ │embeddings       │
├──────────────────┤ ├──────────────┤ ├─────────────────┤
│ id (PK)          │ │ id (PK)      │ │ id (PK)         │
│ recipe_id (FK)   │ │ recipe_id    │ │ recipe_id (FK)  │
│ ingredient_text  │ │ (FK)         │ │ embedding_type  │
│ order_index      │ │ instruction_ │ │ embedding       │
│                  │ │   text       │ │ created_at      │
│                  │ │ step_number  │ │                 │
└──────────────────┘ └───────────────┘ └─────────────────┘
```

---

## SQL Commands for Supabase

Use the following SQL commands to create the tables in your Supabase database. Execute these in the Supabase SQL Editor or via your database client.

### Prerequisites

1. **Enable UUID Extension** (if not already enabled):
   ```sql
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
   ```

2. **Enable pgvector Extension** (for future `recipe_embeddings` table):
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

### Table Creation Scripts

#### 1. Create `recipes` Table

```sql
CREATE TABLE IF NOT EXISTS recipes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR NOT NULL,
    servings VARCHAR,
    total_time VARCHAR,
    source_url VARCHAR,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index on created_at for efficient ordering
CREATE INDEX IF NOT EXISTS idx_recipes_created_at ON recipes(created_at DESC);

-- Create index on title for search operations
CREATE INDEX IF NOT EXISTS idx_recipes_title ON recipes(title);
```

#### 2. Create `recipe_ingredients` Table

```sql
CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    ingredient_text TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    CONSTRAINT unique_recipe_ingredient_order UNIQUE (recipe_id, order_index)
);

-- Create composite index for efficient ordered retrieval
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe_order 
    ON recipe_ingredients(recipe_id, order_index);

-- Create index on recipe_id (though FK index is usually auto-created)
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe_id 
    ON recipe_ingredients(recipe_id);
```

#### 3. Create `recipe_instructions` Table

```sql
CREATE TABLE IF NOT EXISTS recipe_instructions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    instruction_text TEXT NOT NULL,
    step_number INTEGER NOT NULL CHECK (step_number >= 1),
    CONSTRAINT unique_recipe_instruction_step UNIQUE (recipe_id, step_number)
);

-- Create composite index for efficient ordered retrieval
CREATE INDEX IF NOT EXISTS idx_recipe_instructions_recipe_step 
    ON recipe_instructions(recipe_id, step_number);

-- Create index on recipe_id (though FK index is usually auto-created)
CREATE INDEX IF NOT EXISTS idx_recipe_instructions_recipe_id 
    ON recipe_instructions(recipe_id);
```

#### 4. Create `recipe_embeddings` Table (Future)

```sql
-- Note: This table is planned but not yet used in the codebase
-- Requires pgvector extension to be enabled

CREATE TABLE IF NOT EXISTS recipe_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    embedding_type VARCHAR NOT NULL,
    embedding vector(1536), -- Adjust dimension based on your embedding model
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index on recipe_id
CREATE INDEX IF NOT EXISTS idx_recipe_embeddings_recipe_id 
    ON recipe_embeddings(recipe_id);

-- Create index on embedding_type for filtering
CREATE INDEX IF NOT EXISTS idx_recipe_embeddings_type 
    ON recipe_embeddings(embedding_type);

-- Create vector index for similarity search (HNSW is recommended for production)
-- Note: Adjust dimensions and parameters based on your needs
CREATE INDEX IF NOT EXISTS idx_recipe_embeddings_vector 
    ON recipe_embeddings 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

### Trigger for Auto-Updating `updated_at`

Create a trigger function and trigger to automatically update the `updated_at` timestamp:

```sql
-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger on recipes table
CREATE TRIGGER update_recipes_updated_at
    BEFORE UPDATE ON recipes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### Complete Setup Script

Here's a complete script that creates all tables, indexes, and triggers in the correct order:

```sql
-- ============================================
-- ForkFolio Database Schema Setup
-- ============================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- 1. Create recipes table
-- ============================================
CREATE TABLE IF NOT EXISTS recipes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR NOT NULL,
    servings VARCHAR,
    total_time VARCHAR,
    source_url VARCHAR,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recipes_created_at ON recipes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recipes_title ON recipes(title);

-- ============================================
-- 2. Create recipe_ingredients table
-- ============================================
CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    ingredient_text TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    CONSTRAINT unique_recipe_ingredient_order UNIQUE (recipe_id, order_index)
);

CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe_order 
    ON recipe_ingredients(recipe_id, order_index);
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe_id 
    ON recipe_ingredients(recipe_id);

-- ============================================
-- 3. Create recipe_instructions table
-- ============================================
CREATE TABLE IF NOT EXISTS recipe_instructions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    instruction_text TEXT NOT NULL,
    step_number INTEGER NOT NULL CHECK (step_number >= 1),
    CONSTRAINT unique_recipe_instruction_step UNIQUE (recipe_id, step_number)
);

CREATE INDEX IF NOT EXISTS idx_recipe_instructions_recipe_step 
    ON recipe_instructions(recipe_id, step_number);
CREATE INDEX IF NOT EXISTS idx_recipe_instructions_recipe_id 
    ON recipe_instructions(recipe_id);

-- ============================================
-- 4. Create recipe_embeddings table (future)
-- ============================================
CREATE TABLE IF NOT EXISTS recipe_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    embedding_type VARCHAR NOT NULL,
    embedding vector(1536), -- Adjust dimension based on embedding model
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recipe_embeddings_recipe_id 
    ON recipe_embeddings(recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_embeddings_type 
    ON recipe_embeddings(embedding_type);

-- Vector index (commented out - uncomment when ready to use)
-- CREATE INDEX IF NOT EXISTS idx_recipe_embeddings_vector 
--     ON recipe_embeddings 
--     USING hnsw (embedding vector_cosine_ops)
--     WITH (m = 16, ef_construction = 64);

-- ============================================
-- 5. Create trigger for auto-updating updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_recipes_updated_at
    BEFORE UPDATE ON recipes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

---

## Data Types and Constraints

### UUID Generation
- Supabase uses `gen_random_uuid()` for UUID generation
- Alternative: `uuid_generate_v4()` if using `uuid-ossp` extension

### Timestamps
- `NOW()` function sets default timestamps
- `updated_at` is automatically maintained via trigger

### Foreign Key Constraints
- All foreign keys use `ON DELETE CASCADE` to maintain referential integrity
- Deleting a recipe automatically deletes all related ingredients, instructions, and embeddings

### Unique Constraints
- `recipe_ingredients`: Unique `(recipe_id, order_index)` prevents duplicate ordering
- `recipe_instructions`: Unique `(recipe_id, step_number)` prevents duplicate step numbers

### Check Constraints
- `recipe_instructions.step_number >= 1` ensures 1-based step numbering

---

## Migration Notes

### When Deploying to Supabase

1. **Run the complete setup script** in the Supabase SQL Editor
2. **Verify table creation** by checking the Supabase dashboard
3. **Test foreign key constraints** by creating a test recipe with ingredients/instructions
4. **Verify indexes** are created (check in Supabase dashboard under Database → Indexes)

### When Modifying Schema

1. Always test migrations on a development database first
2. Use `IF NOT EXISTS` clauses to make scripts idempotent
3. Consider using Supabase migrations feature for version control
4. Document any breaking changes in migration scripts

---

## Performance Considerations

### Indexes
- Composite indexes on `(recipe_id, order_index)` and `(recipe_id, step_number)` optimize ordered retrieval
- Index on `recipes.created_at` speeds up "recent recipes" queries
- Index on `recipes.title` supports search operations

### Query Optimization
- Use `ORDER BY` with indexed columns for efficient sorting
- Foreign key indexes automatically support JOIN operations
- Consider adding full-text search indexes if implementing advanced search

### Future Optimizations
- Vector indexes (HNSW) for similarity search when `recipe_embeddings` is implemented
- Consider partitioning `recipes` table by date if it grows very large
- Materialized views for common query patterns

---

## Related Documentation

- [Architecture Documentation](./architecture.md) - Overall system architecture
- [Recipe Processing Flow](./recipe-processing-flow.md) - How recipes are processed and stored
