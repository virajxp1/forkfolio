# ForkFolio Architecture

## Scope

This document describes the architecture as implemented today, plus known
production gaps and target controls. It is intentionally operational and avoids
quality grades.

## Current System

ForkFolio is split into:

- FastAPI backend (`app/`) for ingestion, extraction, storage, search, books,
  and grocery-list aggregation.
- Next.js frontend (`apps/web`) for search, browse, recipe detail, book views,
  add-recipe flows, async URL preview polling, experiments, and Supabase-based
  Google sign-in.
- PostgreSQL (Supabase) persistence with connection pooling and pgvector.
- Optional Redis-backed persistence for async URL preview jobs.

## Runtime Layers

1. API layer (`app/api/v1/endpoints/*`): request validation and response
   shaping.
2. Service layer (`app/services/*`): recipe pipeline orchestration and LLM
   integration.
3. Manager/data layer (`app/services/data/managers/*`): SQL access and
   transactional operations.
4. Infrastructure layer: pooled DB connectivity
   (`app/services/data/supabase_client.py`) and optional Redis-backed preview
   job storage (`app/core/job_store.py`, `app/core/redis_client.py`).

## Request Path

1. Request enters FastAPI app (`app/main.py`).
2. Middleware applies body-size limit, timeout, token auth, and rate-limit
   logic.
3. Endpoint handler calls service and manager dependencies.
4. Data is read/written through manager SQL calls.
5. JSON response is returned to the caller.

For async URL preview imports, the path diverges after routing:

1. `POST /api/v1/recipes/preview-from-url/jobs` creates a short-lived preview
   job.
2. `RecipePreviewJobService` drives the job through `queued`, `processing`,
   `completed`, or `failed`, with extraction isolated in a worker process.
3. Jobs are stored in Redis when `REDIS_URL` is configured; otherwise they use
   the process-local TTL cache and are lost on API restart.
4. The frontend polls `GET /api/v1/recipes/preview-from-url/jobs/{job_id}` until
   the preview completes or fails.

Redis persists job state only. Execution is launched from FastAPI background
tasks, so a backend restart does not resume an interrupted job.

## What Is Solid Today

- Clear layering between routing, services, and persistence.
- Transaction-aware DB context management.
- Async URL preview jobs can survive backend restarts when Redis is configured.
- Unit and e2e coverage across major user flows.
- OpenAPI validation integrated in quality checks.

## Known Production Gaps

- Configuration is still environment-coupled in several places (single-service
  assumptions and static infra defaults).
- Rate limiting and most app-level caches are process-local, not distributed.
- URL preview ingestion remains a high-risk surface and needs strict SSRF
  hardening defaults.
- API error semantics are mixed in some flows (`200` with `success: false`).
- Schema evolution does not use committed migration artifacts/tooling.
- Dependency update flow is improving, but still requires disciplined lockfile
  policy and CI enforcement.

## Target Controls For Production Grade

- Fail-closed security defaults (auth required for protected routes).
- Explicit environment segmentation (`dev`/`staging`/`prod`) for data and keys.
- Distributed rate limiting and cache strategy for multi-instance deploys.
- Strict URL preview network policy (HTTPS-only, explicit allowlist model, and
  safer outbound controls).
- Versioned migration workflow in-repo with automated apply/verify in CI.
- Fully reproducible dependency installs in CI/deploy with lockfile freshness
  checks.
- SLO-based monitoring: request latency/error rate, DB connectivity, and queue
  backpressure signals.

## Related Docs

- [Engineering Architecture](engineering-architecture.md)
- [API Reference](api-reference.md)
- [Database Schema](database-schema.md)
- [Recipe Processing Flow](recipe-processing-flow.md)
