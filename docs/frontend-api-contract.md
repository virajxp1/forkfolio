# Frontend API Contract Notes

This document captures the frontend-facing API contract expectations while the
`apps/web` client is being introduced.

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
- Non-2xx responses use FastAPI `detail` payloads for errors.
- Exception: `POST /recipes/process-and-store` may return `200` with
  `success: false` and an `error` field when processing fails.
- IDs are UUID strings.
- The ingestion request field `is_test` is exposed as `isTest` over the wire.

## Recipes Endpoints

- `POST /api/v1/recipes/process-and-store`
  - Ingests raw recipe text and runs cleanup, extraction, deduplication, and storage.
  - Request body:
    - `raw_input` (string, required, min length 10)
    - `enforce_deduplication` (boolean, optional, default `true`)
    - `isTest` (boolean, optional, default `false`)
  - Success response (`200`) includes:
    - `recipe_id`
    - `recipe`
    - `created`
    - `success: true`
    - `message`
  - Processing failure response (`200`) includes:
    - `error`
    - `success: false`

- `GET /api/v1/recipes/search/semantic`
  - Query params:
    - `query` (string, required, min length 2 after trim)
    - `limit` (integer, optional, `1..50`, default `10`)
  - Response includes:
    - `query`
    - `count`
    - `results`
    - `success`

- `GET /api/v1/recipes/{recipe_id}`
  - Returns a recipe with ingredients and instructions.

- `GET /api/v1/recipes/{recipe_id}/all`
  - Returns a recipe including embeddings.

- `DELETE /api/v1/recipes/delete/{recipe_id}`
  - Deletes a recipe by ID.

## Recipe Books Endpoints

- `POST /api/v1/recipe-books/`
  - Creates a recipe book.
  - Request body:
    - `name` (string, required, max length 120)
    - `description` (string, optional, max length 1000)

- `GET /api/v1/recipe-books/`
  - Query params:
    - `name` (optional; when present, fetches one book by name)
    - `limit` (optional, `1..200`, default `50`)

- `GET /api/v1/recipe-books/stats`
  - Returns aggregate recipe-book stats.

- `GET /api/v1/recipe-books/by-recipe/{recipe_id}`
  - Returns books containing a specific recipe.

- `GET /api/v1/recipe-books/{recipe_book_id}`
  - Returns a recipe book by ID.

- `PUT /api/v1/recipe-books/{recipe_book_id}/recipes/{recipe_id}`
  - Adds a recipe to a book (idempotent).

- `DELETE /api/v1/recipe-books/{recipe_book_id}/recipes/{recipe_id}`
  - Removes a recipe from a book.

## Frontend Integration Notes

- Generate and version OpenAPI types from `/openapi.json`.
- Keep client-side data hooks keyed by resource and route params.
- Centralize auth header injection in one fetch/client layer to avoid drift.
