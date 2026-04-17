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
  add-recipe flows, and Supabase-based Google sign-in.
- PostgreSQL (Supabase) persistence with connection pooling and pgvector.

## Runtime Layers

1. API layer (`app/api/v1/endpoints/*`): request validation and response
   shaping.
2. Service layer (`app/services/*`): recipe pipeline orchestration and LLM
   integration.
3. Manager/data layer (`app/services/data/managers/*`): SQL access and
   transactional operations.
4. Infrastructure layer (`app/services/data/supabase_client.py`): pooled DB
   connectivity.

## Request Path

1. Request enters FastAPI app (`app/main.py`).
2. Middleware applies body-size limit, timeout, token auth, and rate-limit
   logic.
3. Endpoint handler calls service and manager dependencies.
4. Data is read/written through manager SQL calls.
5. JSON response is returned to the caller.

## What Is Solid Today

- Clear layering between routing, services, and persistence.
- Transaction-aware DB context management.
- Unit and e2e coverage across major user flows.
- OpenAPI validation integrated in quality checks.

## Known Production Gaps

- Configuration is still environment-coupled in several places (single-service
  assumptions and static infra defaults).
- Rate limiting and app-level caches are process-local, not distributed.
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
