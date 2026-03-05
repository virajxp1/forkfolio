# ForkFolio

A production-ready recipe management API that transforms raw recipe text into structured, searchable data using AI-powered processing pipelines.

## What It Does

ForkFolio helps teams ingest messy recipe content and turn it into clean API-accessible records.

- Accepts raw recipe text and returns structured recipe data.
- Stores recipes, ingredients, instructions, and embeddings.
- Supports semantic search across recipes.
- Supports recipe book creation and recipe-to-book organization.

## API Documentation

ForkFolio includes generated OpenAPI 3.1 documentation:

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

For endpoint-by-endpoint documentation, request/response examples, and auth details, see:

- [Detailed API Reference](docs/api-reference.md)

Protected operations in the OpenAPI contract include both supported auth styles:

- `X-API-Token` header
- `Authorization: Bearer <API_AUTH_TOKEN>`

The OpenAPI contract also documents common middleware/runtime responses:

- `401` Unauthorized (protected endpoints)
- `413` Request too large
- `429` Rate limit exceeded (protected endpoints)
- `500` Internal server error
- `504` Request timeout

## Authentication

Protected routes accept either:

- `X-API-Token: <API_AUTH_TOKEN>`
- `Authorization: Bearer <API_AUTH_TOKEN>`

Public routes:

- `GET /api/v1/`
- `GET /api/v1/health`

## API Contract Validation

OpenAPI compliance and required auth/error contracts are validated via:

- `make validate-openapi`

`make lint` runs this validation automatically in CI.

## Engineering Documentation

Architecture and implementation details are documented separately:

- [Engineering Architecture](docs/engineering-architecture.md)
- [Frontend Design](docs/frontend-design.md)
- [Frontend API Contract Notes](docs/frontend-api-contract.md)

## Frontend Status

ForkFolio includes a Next.js frontend in `apps/web` so backend and UI can evolve
in the same repository.

### Frontend Stack

- Runtime/tooling: Node.js + npm
- Framework: Next.js (App Router) + TypeScript
- UI styling: Tailwind CSS
- UI component system: `shadcn/ui`

### Implemented Slices

- Landing page (`/`)
- Semantic recipe browse/search (`/browse`)
- Recipe detail page (`/recipes/[recipeId]`)
- Recipe ingestion flow (`/recipes/new`)
- Internal API proxy routes for frontend-to-backend requests

### Remaining Frontend Work

1. Add auth-aware protected shell and session handling.
2. Implement recipe books management UX.
3. Add frontend unit/e2e test coverage.
4. Tighten generated API typing workflow from `/openapi.json`.

## Frontend UI Rules

- Use `shadcn/ui` components as the default for all UI primitives and patterns.
- Use library components/compositions first, always.
- Do not build custom components when an equivalent library component exists.
- If custom UI is required, compose from `shadcn/ui` primitives instead of raw-from-scratch implementations.
