# ForkFolio

ForkFolio is a production-oriented recipe platform with:

- A Python/FastAPI backend (`app/`) for ingestion, extraction, storage, search, books, and grocery-list aggregation.
- A Next.js frontend (`apps/web`) for browse, recipe detail, books, bag/checkout, and URL/manual recipe import flows.

This README is the release runbook for local setup, quality gates, and deploy.

## System Overview

Core capabilities:

- Process and store recipes from raw text.
- Preview recipe extraction from URL before saving.
- Semantic search over recipes.
- Recipe books (create/list/detail/add/remove).
- Grocery list aggregation from selected recipes.
- Recipe deletion and custom not-found UX on the frontend.

Primary docs:

- API reference: [docs/api-reference.md](docs/api-reference.md)
- Engineering architecture: [docs/engineering-architecture.md](docs/engineering-architecture.md)
- Frontend design notes: [docs/frontend-design.md](docs/frontend-design.md)
- Frontend API contract notes: [docs/frontend-api-contract.md](docs/frontend-api-contract.md)
- Frontend-specific setup/deploy: [apps/web/README.md](apps/web/README.md)

## Runtime Pinning

Python is pinned to `3.11` for consistency across local, CI, and deploy:

- `.python-version` => `3.11`
- CI workflows use Python `3.11`
- Docker uses `python:3.11-slim`
- Render backend runtime is pinned with `PYTHON_VERSION=3.11.11` in `render.yaml`

## Local Setup

### 1) Backend

Bootstrap Python environment:

```bash
make setup-python
```

Run API:

```bash
make run
```

API base path defaults to:

- `http://localhost:8000/api/v1`

### 2) Frontend

Install and run:

```bash
cd apps/web
npm ci
npm run dev
```

Frontend reads env from repo-root `.env` via `apps/web/scripts/run-with-root-env.mjs`.

## Environment Variables

Backend (required in deployed environments):

- `API_AUTH_TOKEN`
- `OPEN_ROUTER_API_KEY`
- `SUPABASE_PASSWORD`

Frontend runtime vars:

- `FORKFOLIO_API_BASE_URL` (example: `https://forkfolio-be.onrender.com`)
- `FORKFOLIO_API_BASE_PATH` (usually `/api/v1`)
- `FORKFOLIO_API_TOKEN` (required when backend token middleware is enabled)

## Quality Gates (Release Criteria)

Backend:

```bash
make lint
make test
make test-e2e
```

Frontend:

```bash
npm --prefix apps/web run lint
npm --prefix apps/web run test
npm --prefix apps/web run test:coverage
npm --prefix apps/web run build
```

CI workflows:

- `.github/workflows/lint.yml`
- `.github/workflows/test.yml`

## Deployment

### Backend (Render)

`render.yaml` contains backend service config:

- Runtime: Python
- Build: `pip install -r requirements.txt`
- Start: `python3 scripts/run.py`
- Health check: `/api/v1/health`

### Frontend (Render)

Use a separate Render Web Service for `apps/web`.

Canonical FE deploy steps (commands, env vars, health check) are documented in:

- [apps/web/README.md](apps/web/README.md)

## Release Checklist

1. Branch is synced with `main`.
2. All backend and frontend quality gates pass.
3. OpenAPI contract validation passes (`make validate-openapi` or `make lint`).
4. Render env vars are present and correct for backend and frontend services.
5. Smoke-test key user flows on deployed FE:
   - Browse + open recipe
   - Add recipe (manual and URL preview)
   - Books add/remove
   - Bag -> grocery list generation
   - Delete recipe -> custom not-found page

## Auth + Public Endpoints

Protected endpoints support both:

- `X-API-Token: <API_AUTH_TOKEN>`
- `Authorization: Bearer <API_AUTH_TOKEN>`

Public endpoints:

- `GET /api/v1/`
- `GET /api/v1/health`

## API Docs (Runtime)

Available from backend service:

- Swagger: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`
