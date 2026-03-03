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
