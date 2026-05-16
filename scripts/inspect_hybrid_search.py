"""Smoke-test inspector for Postgres hybrid recipe search.

Usage:
    .venv/bin/python -m scripts.inspect_hybrid_search --query "lasanga"
"""

from __future__ import annotations

import argparse
import json

from app.core.config import settings
from app.services.recipe_embeddings_impl import RecipeEmbeddingsServiceImpl
from app.services.recipe_hybrid_search_impl import RecipeHybridSearchServiceImpl


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect Postgres hybrid recipe search."
    )
    parser.add_argument("--query", required=True, help="Free-text recipe query.")
    parser.add_argument("--limit", type=int, default=10, help="Max results to print.")
    args = parser.parse_args()

    print("Search config")
    print(f"  max_distance:      {settings.SEMANTIC_SEARCH_V2_MAX_DISTANCE}")
    print(f"  trigram_threshold: {settings.SEMANTIC_SEARCH_V2_TRIGRAM_THRESHOLD}")
    print(f"  min_score:         {settings.SEMANTIC_SEARCH_V2_MIN_SCORE}")
    print(
        "  weights:           "
        f"fts={settings.SEMANTIC_SEARCH_V2_FTS_WEIGHT} "
        f"trigram={settings.SEMANTIC_SEARCH_V2_TRIGRAM_WEIGHT} "
        f"vector={settings.SEMANTIC_SEARCH_V2_VECTOR_WEIGHT}"
    )

    embeddings_service = RecipeEmbeddingsServiceImpl()
    search_service = RecipeHybridSearchServiceImpl()
    query_embedding = embeddings_service.embed_search_query(args.query)
    results = search_service.search(
        query=args.query,
        query_embedding=query_embedding,
        limit=max(1, args.limit),
    )

    print("\nResults")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
