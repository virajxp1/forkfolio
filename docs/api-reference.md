# ForkFolio API Reference

## OpenAPI Contract

- Standard: OpenAPI `3.1`
- OpenAPI JSON: `/openapi.json`
- Swagger UI: `/docs`
- ReDoc: `/redoc`

## Base URL

- Local: `http://localhost:8000`
- Production: `https://<your-service-domain>`
- API base path: `/api/v1`

## Authentication

ForkFolio supports two token styles for protected endpoints:

- `X-API-Token: <API_AUTH_TOKEN>`
- `Authorization: Bearer <API_AUTH_TOKEN>`

Public endpoints (no token required):

- `GET /api/v1/`
- `GET /api/v1/health`

## Common Error Responses

Error payload shape:

```json
{
  "detail": "Error message"
}
```

Common status codes:

- `401` Unauthorized (protected endpoints only)
- `413` Request payload too large
- `429` Rate limit exceeded (protected endpoints only, includes `Retry-After` header)
- `500` Internal server error
- `504` Request timeout
- `422` Request validation error (path/query/body validation)

## Health Endpoints

### `GET /api/v1/`

Auth: Public

Returns a basic API welcome payload.

Example response:

```json
{
  "message": "Welcome to ForkFolio API"
}
```

### `GET /api/v1/health`

Auth: Public

Returns lightweight liveness status.

Example response:

```json
{
  "status": "ok"
}
```

## Recipes Endpoints

### `POST /api/v1/recipes/process-and-store`

Auth: Required

Runs the ingestion pipeline for raw recipe input and stores the result.

Request body:

```json
{
  "raw_input": "Chocolate Chip Cookies\n\nIngredients:\n- 2 cups flour\n- 1 cup sugar\n\nInstructions:\n1. Mix\n2. Bake",
  "enforce_deduplication": true,
  "isTest": false
}
```

Field notes:

- `raw_input` (string, required, min length `10`)
- `enforce_deduplication` (boolean, optional, default `true`)
- `isTest` (boolean, optional, default `false`; `is_test` also accepted)

Success response (created):

```json
{
  "recipe_id": "uuid",
  "recipe": {},
  "success": true,
  "created": true,
  "message": "Recipe processed and stored successfully"
}
```

Success response (duplicate):

```json
{
  "recipe_id": "uuid",
  "recipe": {},
  "success": true,
  "created": false,
  "message": "Duplicate recipe found; returning existing recipe."
}
```

Pipeline error payload:

```json
{
  "error": "Error details",
  "success": false
}
```

### `POST /api/v1/recipes/preview-from-url`

Scrapes recipe content from a URL and returns a cleaned preview payload without
saving anything to the database.

Request body:

```json
{
  "start_url": "https://www.example.com/recipes/pasta",
  "target_instruction": "Extract the full recipe text from this page.",
  "max_steps": 10,
  "max_actions_per_step": 2
}
```

Field notes:

- `start_url` (string, required, must be a public `http/https` URL)
- `target_instruction` (string, required)
- `target_prompt` (string, optional alias for `target_instruction`)
- `max_steps` (integer, optional, default `10`, min `1`, max `50`)
- `max_actions_per_step` (integer, optional, default `2`, min `1`, max `4`)

Success response:

```json
{
  "success": true,
  "preview": {
    "source_url": "https://www.example.com/recipes/pasta",
    "target_instruction": "Extract the full recipe text from this page.",
    "raw_scraped_text": "raw text captured from page",
    "cleaned_text": "cleaned recipe text",
    "recipe": {},
    "extraction_error": null,
    "evidence": "evidence from page",
    "confidence": 0.82,
    "trace_steps": 3
  },
  "save_payload": {
    "raw_input": "cleaned recipe text"
  },
  "message": "Recipe preview generated successfully"
}
```

Preview error response (HTTP 200 with `success=false`):

```json
{
  "error": "URL scrape failed: ...",
  "success": false
}
```

### `GET /api/v1/recipes/search/semantic`

Auth: Required

Performs semantic similarity search over recipe embeddings.

Query parameters:

- `query` (string, required, minimum 2 non-whitespace chars)
- `limit` (integer, optional, default `10`, min `1`, max `50`)

Success response:

```json
{
  "query": "chocolate cookies",
  "count": 2,
  "results": [],
  "success": true
}
```

### `GET /api/v1/recipes/{recipe_id}`

Auth: Required

Returns a recipe with ingredients and instructions.

Success response:

```json
{
  "recipe": {},
  "success": true
}
```

Not found:

```json
{
  "detail": "Recipe not found"
}
```

### `GET /api/v1/recipes/{recipe_id}/all`

Auth: Required

Returns a recipe including embeddings.

Success response:

```json
{
  "recipe": {},
  "success": true
}
```

### `DELETE /api/v1/recipes/delete/{recipe_id}`

Auth: Required

Deletes a recipe by ID.

Success response:

```json
true
```

## Recipe Books Endpoints

### `POST /api/v1/recipe-books/`

Auth: Required

Creates a recipe book.

Request body:

```json
{
  "name": "Weeknight Dinners",
  "description": "Simple weekday meals"
}
```

Success response:

```json
{
  "recipe_book": {},
  "created": true,
  "success": true
}
```

### `GET /api/v1/recipe-books/`

Auth: Required

Lists recipe books, or fetches one by name.

Query parameters:

- `name` (string, optional)
- `limit` (integer, optional, default `50`, min `1`, max `200`)

Success response (list):

```json
{
  "recipe_books": [],
  "success": true
}
```

Success response (by name):

```json
{
  "recipe_book": {},
  "success": true
}
```

### `GET /api/v1/recipe-books/stats`

Auth: Required

Returns aggregate recipe book statistics.

Success response:

```json
{
  "stats": {},
  "success": true
}
```

### `GET /api/v1/recipe-books/by-recipe/{recipe_id}`

Auth: Required

Returns all recipe books that include the specified recipe.

Success response:

```json
{
  "recipe_id": "uuid",
  "recipe_books": [],
  "success": true
}
```

### `GET /api/v1/recipe-books/{recipe_book_id}`

Auth: Required

Returns a recipe book by ID.

Success response:

```json
{
  "recipe_book": {},
  "success": true
}
```

### `PUT /api/v1/recipe-books/{recipe_book_id}/recipes/{recipe_id}`

Auth: Required

Adds a recipe to a recipe book (idempotent).

Success response:

```json
{
  "recipe_book_id": "uuid",
  "recipe_id": "uuid",
  "added": true,
  "success": true
}
```

### `DELETE /api/v1/recipe-books/{recipe_book_id}/recipes/{recipe_id}`

Auth: Required

Removes a recipe from a recipe book.

Success response:

```json
{
  "recipe_book_id": "uuid",
  "recipe_id": "uuid",
  "removed": true,
  "success": true
}
```
