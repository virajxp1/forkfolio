# ForkFolio

A production-ready recipe management API that transforms raw recipe text into structured, searchable data using AI-powered processing pipelines.

## What It Does

ForkFolio helps teams ingest messy recipe content and turn it into clean API-accessible records.

- Accepts raw recipe text and returns structured recipe data.
- Stores recipes, ingredients, instructions, and embeddings.
- Supports semantic search across recipes.
- Supports recipe book creation and recipe-to-book organization.

## API Documentation

ForkFolio includes generated OpenAPI documentation:

- Swagger UI: `/docs`
- ReDoc: `/redoc`

For endpoint-by-endpoint documentation, request/response examples, and auth details, see:

- [Detailed API Reference](docs/api-reference.md)

## Authentication

Protected routes accept either:

- `X-API-Token: <API_AUTH_TOKEN>`
- `Authorization: Bearer <API_AUTH_TOKEN>`

Public routes:

- `GET /api/v1/`
- `GET /api/v1/health`

## Engineering Documentation

Architecture and implementation details are documented separately:

- [Engineering Architecture](docs/engineering-architecture.md)
- [Frontend Design](docs/frontend-design.md)
- [Frontend API Contract Notes](docs/frontend-api-contract.md)

## Frontend Plan (Next Steps)

ForkFolio will add a frontend in the same repository so backend and UI can evolve together.

### Stack

- Runtime/tooling: Node.js
- Framework: Next.js (App Router) + TypeScript
- Package/workspace management: `pnpm` workspace layout
- UI styling: Tailwind CSS
- UI component system: `shadcn/ui`
- API state/data fetching: TanStack Query
- API typing: OpenAPI-generated TypeScript types from this FastAPI service

### Near-Term Implementation Steps

1. Scaffold `apps/web` with Next.js + TypeScript and workspace wiring.
2. Add shared API client/types generation from `/openapi.json`.
3. Implement auth flow and protected page shell.
4. Build first feature slices: recipe list, recipe detail, search.
5. Add baseline frontend test coverage (unit + basic end-to-end smoke paths).

## Frontend UI Rules

- Use `shadcn/ui` components as the default for all UI primitives and patterns.
- Use library components/compositions first, always.
- Do not build custom components when an equivalent library component exists.
- If custom UI is required, compose from `shadcn/ui` primitives instead of raw-from-scratch implementations.
