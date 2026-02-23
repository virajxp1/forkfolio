# Engineering Architecture

This document contains implementation-focused details that are intentionally separate from the public-facing README.

## System Overview

ForkFolio is a FastAPI service with three main concerns:

- API routing and request protection middleware.
- AI-powered recipe ingestion and semantic retrieval.
- PostgreSQL-backed persistence (Supabase) with connection pooling.

## Request Lifecycle

1. Request enters FastAPI app (`app/main.py`).
2. Middleware applies size limits, rate limits, timeout, and optional auth token checks.
3. Router dispatches to endpoint handlers in `app/api/v1/endpoints/`.
4. Endpoint handlers call service and manager layers from `app/services/`.
5. Data is persisted and queried through manager classes and pooled DB connections.

## Key Components

- `app/main.py`
- `app/core/middleware.py`
- `app/api/v1/endpoints/recipes.py`
- `app/api/v1/endpoints/recipe_books.py`
- `app/services/recipe_processing_service.py`
- `app/services/data/managers/recipe_manager.py`
- `app/services/data/managers/recipe_book_manager.py`
- `app/services/data/supabase_client.py`

## Data and Processing Notes

- Recipe ingestion pipeline combines cleanup, extraction, deduplication, embedding generation, and storage.
- Semantic search is backed by embedding similarity checks against stored recipe vectors.
- Health endpoint is lightweight by design and avoids DB/LLM dependencies.

## Related Docs

- [API Reference](api-reference.md)
- [Architecture Notes](architecture.md)
- [Recipe Processing Flow](recipe-processing-flow.md)
- [Database Schema](database-schema.md)
