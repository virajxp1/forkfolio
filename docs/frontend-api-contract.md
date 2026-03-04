# Frontend API Contract Notes

This document captures the frontend-facing API contract for the `apps/web`
client.

## Base URL and Auth

- Base path: `/api/v1`
- Public routes:
  - `GET /api/v1/`
  - `GET /api/v1/health`
- Protected routes accept either:
  - `X-API-Token: <API_AUTH_TOKEN>`
  - `Authorization: Bearer <API_AUTH_TOKEN>`

## Request/Response Conventions

- Most successful responses include `success: true`.
- Non-2xx responses return FastAPI `detail` payloads.
- `POST /recipes/process-and-store` can return `200` with `success: false` and
  an `error` field when processing fails.
- IDs are UUID strings.
- In ingestion payloads, `isTest` is mapped to backend field `is_test`.

## Current Contract Used by Browse UI

### 1) Semantic Search

- Endpoint: `GET /api/v1/recipes/search/semantic?query=<string>&limit=<int>`
- Response shape consumed by frontend:

```json
{
  "query": "pasta",
  "count": 2,
  "results": [
    {
      "id": "uuid",
      "name": "Herby Pasta",
      "distance": 0.09,
      "rerank_score": 0.97,
      "embedding_score": 0.91,
      "combined_score": 0.95,
      "raw_rerank_score": 0.9,
      "rerank_mode": "fallback",
      "cuisine_boost": 0.15,
      "family_boost": 0.1
    }
  ],
  "success": true
}
```

Notes:
- Always expected from search formatter: `id`, `name`, `distance`.
- Optional rerank fields: `rerank_score`, `embedding_score`,
  `combined_score`, `raw_rerank_score`, `rerank_mode`, `cuisine_boost`,
  `family_boost`.

### 2) Recipe Detail

- Endpoint: `GET /api/v1/recipes/{recipe_id}`
- Response shape consumed by frontend:

```json
{
  "recipe": {
    "id": "uuid",
    "title": "Herby Pasta",
    "servings": "2",
    "total_time": "20 minutes",
    "source_url": "https://...",
    "is_test_data": false,
    "created_at": "2026-03-03T00:00:00+00:00",
    "updated_at": "2026-03-03T00:00:00+00:00",
    "ingredients": ["200g pasta", "olive oil", "herbs"],
    "instructions": ["Boil pasta", "Toss with sauce"]
  },
  "success": true
}
```

## Other Available Endpoints

### Recipes

- `POST /api/v1/recipes/process-and-store`
- `GET /api/v1/recipes/{recipe_id}`
- `GET /api/v1/recipes/{recipe_id}/all`
- `DELETE /api/v1/recipes/delete/{recipe_id}`

### Recipe Books

- `POST /api/v1/recipe-books/`
- `GET /api/v1/recipe-books/`
- `GET /api/v1/recipe-books/stats`
- `GET /api/v1/recipe-books/by-recipe/{recipe_id}`
- `GET /api/v1/recipe-books/{recipe_book_id}`
- `PUT /api/v1/recipe-books/{recipe_book_id}/recipes/{recipe_id}`
- `DELETE /api/v1/recipe-books/{recipe_book_id}/recipes/{recipe_id}`

## Frontend Integration Notes

- Generate and version OpenAPI types from `/openapi.json`.
- Keep hooks and cache keys aligned to route params.
- Centralize auth header injection in one API client layer.
