# ForkFolio Web

Search-first frontend for ForkFolio, built with Next.js + `shadcn/ui`.

## Setup

`apps/web` reads env from the repo root `../../.env`.

1. Add API values in repo root `.env`:
   - `FORKFOLIO_API_BASE_URL` (default: `http://localhost:8000`)
   - `FORKFOLIO_API_BASE_PATH` (default: `/api/v1`)
   - `FORKFOLIO_API_TOKEN` (optional, required when backend token middleware is enabled)
   - `NEXT_PUBLIC_SUPABASE_URL` (required for Google sign-in)
   - `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (required for Google sign-in)
   - `FORKFOLIO_APP_ORIGIN` (optional but recommended in production; canonical app origin for auth callback redirects)

## Run

```bash
npm ci
npm run dev
```

`npm run dev/build/start` automatically loads env from repo-root `.env`.
Open `http://localhost:3000`.

## Supabase Auth

Google sign-in is wired through Supabase Auth using the callback route at
`/auth/callback`.

For production, set `FORKFOLIO_APP_ORIGIN` to your canonical app URL
(for example, `https://app.your-domain.com`) so callback redirects do not rely
on forwarded-host headers.

In Supabase:

1. Enable the Google provider and paste your Google client ID + secret.
2. Add your app URL to the Supabase site URL / redirect allow list.
3. Add the Supabase Google callback URL from the provider screen to the Google
   OAuth client redirect URIs.
4. Run [`docs/supabase-auth-profile-schema.sql`](../../docs/supabase-auth-profile-schema.sql)
   in the Supabase SQL editor to create `public.profiles`.

## Current Routes

App pages:
- `/` landing page
- `/browse` search page with recipe result cards and modal detail view
- `/recipes/[recipeId]` full recipe detail page (direct-link route)
- `/recipes/new` add-recipe ingestion page
- `/books` recipe books list/create page
- `/books/[bookId]` recipe book detail page
- `/bag` grocery bag and consolidated list page
- `/experiment` recipe experimentation chat page
- `/auth/auth-code-error` OAuth callback failure page

Auth and internal API routes:
- `/auth/callback` Supabase OAuth code exchange route
- `/api/search` semantic search proxy route
- `/api/search/names` name-search proxy route
- `/api/recipes` recipe list proxy route
- `/api/recipes/[recipeId]` recipe detail proxy route
- `/api/recipes/process` process-and-store proxy route
- `/api/recipes/preview` URL preview proxy route
- `/api/recipes/grocery-list` grocery aggregation proxy route
- `/api/recipe-books` recipe books list/create proxy route
- `/api/recipe-books/[recipeBookId]` recipe book detail proxy route
- `/api/recipe-books/stats` recipe book stats proxy route
- `/api/recipe-books/by-recipe/[recipeId]` recipe membership proxy route
- `/api/recipe-books/[recipeBookId]/recipes/[recipeId]` recipe membership mutation proxy route
- `/api/experiments/threads` experiment thread list/create proxy route
- `/api/experiments/threads/[threadId]` experiment thread detail proxy route
- `/api/experiments/threads/[threadId]/messages` experiment message post proxy route
- `/api/experiments/threads/[threadId]/messages/stream` experiment streaming proxy route

## Quality Checks

```bash
npm run lint
npm run build
npm run test
npm run test:coverage
```

## Deploy (Frontend)

Deploy `apps/web` on any Node-compatible host.

1. Runtime: `Node 20`
2. Root directory: `apps/web`
3. Build command:

```bash
npm ci && npm run build
```

4. Start command:

```bash
npm run start
```

5. Health check path: `/`
6. Environment variables:
   - `NODE_ENV=production`
   - `NODE_VERSION=20` (if your provider supports this variable)
   - `FORKFOLIO_API_BASE_URL=https://api.your-domain.com`
   - `FORKFOLIO_API_BASE_PATH=/api/v1`
   - `FORKFOLIO_API_TOKEN=<token>` (required only if backend auth middleware is enabled)
   - `NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<publishable-key-or-anon-key>`
   - `FORKFOLIO_APP_ORIGIN=https://app.your-domain.com`

Notes:
- Do not add `apps/web/.env*` files for deployment.
- `npm run dev/build/start` already uses `scripts/run-with-root-env.mjs`; in hosted environments it reads process env vars.
