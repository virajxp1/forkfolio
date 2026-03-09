# ForkFolio Web

Search-first frontend for ForkFolio, built with Next.js + `shadcn/ui`.

## Setup

`apps/web` reads env from the repo root `../../.env`.

1. Add API values in repo root `.env`:
   - `FORKFOLIO_API_BASE_URL` (default: `https://forkfolio-be.onrender.com`)
   - `FORKFOLIO_API_BASE_PATH` (default: `/api/v1`)
   - `FORKFOLIO_API_TOKEN` (optional, required when backend token middleware is enabled)

## Run

```bash
npm install
npm run dev
```

`npm run dev/build/start` automatically loads env from repo-root `.env`.
Open `http://localhost:3000`.

## Current Pages

- `/` landing page
- `/browse` search page with recipe result cards and modal detail view
- `/recipes/[recipeId]` full recipe detail page (direct-link route)
- `/recipes/new` add-recipe ingestion page
- `/api/search` internal search proxy route
- `/api/recipes/[recipeId]` internal recipe detail proxy route
- `/api/recipes/process` internal process-and-store proxy route

## Quality Checks

```bash
npm run lint
npm run build
npm run test
npm run test:coverage
```
