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
