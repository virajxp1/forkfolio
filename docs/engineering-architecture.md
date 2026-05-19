# Engineering Architecture

This document contains implementation-focused details that are intentionally separate from the public-facing README.

## System Overview

ForkFolio is a FastAPI service with three main concerns:

- API routing and request protection middleware.
- AI-powered recipe ingestion and hybrid retrieval.
- PostgreSQL-backed persistence (Supabase) with connection pooling.
- Optional Redis-backed persistence for async recipe preview jobs.

The web frontend (`apps/web`) consumes these APIs and includes Supabase Google
OAuth session handling for profile-aware UI state.

## Request Lifecycle

1. Request enters FastAPI app (`app/main.py`).
2. Middleware applies size limits, rate limits, timeout, and optional auth token checks.
3. Router dispatches to endpoint handlers in `app/api/v1/endpoints/`.
4. Endpoint handlers call service and manager layers from `app/services/`.
5. Data is persisted and queried through manager classes and pooled DB connections.

Async URL preview imports use a second path:

1. `POST /api/v1/recipes/preview-from-url/jobs` creates a preview job.
2. `RecipePreviewJobService` processes the URL in the background and updates
   job state.
3. `app/core/job_store.py` persists the job in Redis when `REDIS_URL` is set,
   otherwise in the process-local TTL cache.
4. The frontend polls `GET /api/v1/recipes/preview-from-url/jobs/{job_id}` for
   completion.

Redis persists job state only. The actual preview extraction still runs inside
FastAPI background tasks, so interrupted in-flight jobs are not resumed by
Redis after a restart.

## Key Components

- `app/main.py`
- `app/core/middleware.py`
- `app/core/job_store.py`
- `app/api/v1/endpoints/recipes.py`
- `app/api/v1/endpoints/recipe_books.py`
- `app/services/recipe_processing_service.py`
- `app/services/recipe_preview_job_service.py`
- `app/services/data/managers/recipe_manager.py`
- `app/services/data/managers/recipe_book_manager.py`
- `app/services/data/supabase_client.py`

## Data and Processing Notes

- Recipe ingestion pipeline combines cleanup, extraction, deduplication, embedding generation, and storage.
- Async URL preview jobs reuse the same extraction pipeline but expose queued /
  processing / completed / failed state for frontend polling.
- Recipe search combines PostgreSQL full-text search, `pg_trgm`, and stored embedding vectors in one hybrid ranking pass.
- `app/core/cache.py` is process-local only; Redis is currently used for
  preview job persistence rather than as a general cache backend.
- Health endpoint is lightweight by design and avoids DB/LLM dependencies.

## Related Docs

- [API Reference](api-reference.md)
- [Architecture Notes](architecture.md)
- [Recipe Processing Flow](recipe-processing-flow.md)
- [Database Schema](database-schema.md)
