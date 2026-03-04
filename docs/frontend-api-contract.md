# Frontend API Contract Notes

This document captures the API response shape the frontend currently relies on
for Search and Recipe Detail flows.

## Current Contract (Implemented)

Base path: `/api/v1`

### 1) Semantic Search

Endpoint: `GET /api/v1/recipes/search/semantic?query=<string>&limit=<int>`

Response shape used by frontend:

```json
{
  "query": "pasta",
  "count": 2,
  "results": [
    {
      "id": "uuid",
      "name": "Herby Pasta",
      "distance": 0.09,
      "rerank_score": 0.97,
      "embedding_score": 0.91,
      "combined_score": 0.95,
      "raw_rerank_score": 0.9,
      "rerank_mode": "fallback",
      "cuisine_boost": 0.15,
      "family_boost": 0.1
    }
  ],
  "success": true
}
```

Notes:
- Guaranteed by DB search formatter: `id`, `name`, `distance`.
- Optional when reranker logic applies: `rerank_score`, `embedding_score`,
  `combined_score`, `raw_rerank_score`, `rerank_mode`, `cuisine_boost`,
  `family_boost`.

### 2) Recipe Detail

Endpoint: `GET /api/v1/recipes/{recipe_id}`

Response shape used by frontend:

```json
{
  "recipe": {
    "id": "uuid",
    "title": "Herby Pasta",
    "servings": "2",
    "total_time": "20 minutes",
    "source_url": "https://...",
    "is_test_data": false,
    "created_at": "2026-03-03T00:00:00+00:00",
    "updated_at": "2026-03-03T00:00:00+00:00",
    "ingredients": ["200g pasta", "olive oil", "herbs"],
    "instructions": ["Boil pasta", "Toss with sauce"]
  },
  "success": true
}
```

Notes:
- Payload is built from `recipes` table (`r.*`) plus aggregated `ingredients`
  and `instructions`.
- Frontend uses this endpoint for full detail and currently also for card
  preview enrichment.

## Contract Gap For Search Cards

Current search results do not include card preview fields (`servings`,
`total_time`, ingredient snippets), so frontend does N+1 detail fetches to build
result cards.
