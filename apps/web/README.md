# ForkFolio Web

Search-first frontend for ForkFolio, built with Next.js + `shadcn/ui`.

## Setup

`apps/web` now loads env from the repo root (`../../.env`) as well.

1. Add API values in repo root `.env` (or `apps/web/.env.local` to override):
   - `FORKFOLIO_API_BASE_URL` (default: `https://forkfolio-be.onrender.com`)
   - `FORKFOLIO_API_BASE_PATH` (default: `/api/v1`)
   - `FORKFOLIO_API_TOKEN` (optional, required when backend token middleware is enabled)

## Run

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

## Current Pages

- `/` landing page with primary actions (add recipe / browse recipes)
- `/browse` search page with recipe result cards
- `/add-recipe` add recipe mock (URL import + manual entry tabs)
- `/recipes/[recipeId]` full recipe detail page

## Quality Checks

```bash
npm run lint
npm run build
```
