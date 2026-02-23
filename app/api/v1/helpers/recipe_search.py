from app.core.logging import get_logger

logger = get_logger(__name__)

WRAPPING_QUOTES = {'"', "'"}


def normalize_search_query(raw_query: str) -> str:
    normalized = " ".join(raw_query.strip().split())
    if (
        len(normalized) >= 2
        and normalized[0] == normalized[-1]
        and normalized[0] in WRAPPING_QUOTES
    ):
        normalized = " ".join(normalized[1:-1].strip().split())
    return normalized


def _normalize_recipe_id(recipe_id: object) -> str | None:
    if recipe_id is None:
        return None
    return str(recipe_id)


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _embedding_score_from_distance(distance_value: object) -> float:
    # Lower cosine distance is better; map to a 0..1 score.
    distance = _to_float(distance_value)
    if distance is None:
        return 0.0
    bounded_distance = min(max(distance, 0.0), 1.0)
    return 1.0 - bounded_distance


def build_rerank_candidates(matches: list[dict], recipe_manager) -> list[dict]:
    recipe_ids = []
    for item in matches:
        recipe_id = _normalize_recipe_id(item.get("id"))
        if recipe_id:
            recipe_ids.append(recipe_id)

    ingredient_previews: dict[str, list[str]] = {}
    if recipe_ids:
        try:
            ingredient_previews = recipe_manager.get_ingredient_previews(
                recipe_ids=recipe_ids,
                max_ingredients=8,
            )
        except Exception as exc:
            logger.warning(
                "Failed to load ingredient previews for rerank candidates: %s",
                exc,
            )

    candidates: list[dict] = []
    for item in matches:
        recipe_id = _normalize_recipe_id(item.get("id"))
        candidates.append(
            {
                "id": recipe_id,
                "name": item.get("name"),
                "distance": item.get("distance"),
                "ingredients_preview": list(ingredient_previews.get(recipe_id, [])),
            }
        )
    return candidates


def apply_rerank(
    matches: list[dict],
    ranked_items: list[dict],
    limit: int,
    min_rerank_score: float = 0.40,
    rerank_weight: float = 0.70,
) -> list[dict]:
    if not ranked_items:
        return matches[:limit]

    match_by_id = {}
    for item in matches:
        recipe_id = _normalize_recipe_id(item.get("id"))
        if recipe_id is not None:
            match_by_id[recipe_id] = item

    ordered_matches: list[dict] = []
    used_ids: set[str] = set()
    ranked_ids_found = False
    normalized_min_score = min(max(min_rerank_score, 0.0), 1.0)
    normalized_rerank_weight = min(max(rerank_weight, 0.0), 1.0)

    for ranked in ranked_items:
        recipe_id = _normalize_recipe_id(ranked.get("id"))
        if recipe_id is None or recipe_id in used_ids or recipe_id not in match_by_id:
            continue
        ranked_ids_found = True
        rerank_score = _to_float(ranked.get("score"))
        if rerank_score is None or rerank_score < normalized_min_score:
            continue

        row = dict(match_by_id[recipe_id])
        embedding_score = _embedding_score_from_distance(row.get("distance"))
        combined_score = (normalized_rerank_weight * rerank_score) + (
            (1.0 - normalized_rerank_weight) * embedding_score
        )
        row["rerank_score"] = rerank_score
        row["embedding_score"] = embedding_score
        row["combined_score"] = combined_score
        ordered_matches.append(row)
        used_ids.add(recipe_id)

    if not ranked_ids_found:
        return matches[:limit]
    if not ordered_matches:
        return []

    ordered_matches.sort(key=lambda item: item.get("combined_score", 0.0), reverse=True)
    return ordered_matches[:limit]
