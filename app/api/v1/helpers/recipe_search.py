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

    for ranked in ranked_items:
        recipe_id = _normalize_recipe_id(ranked.get("id"))
        if recipe_id is None or recipe_id in used_ids or recipe_id not in match_by_id:
            continue
        row = dict(match_by_id[recipe_id])
        row["rerank_score"] = ranked.get("score")
        ordered_matches.append(row)
        used_ids.add(recipe_id)

    for item in matches:
        recipe_id = _normalize_recipe_id(item.get("id"))
        if recipe_id is not None and recipe_id in used_ids:
            continue
        ordered_matches.append(item)

    return ordered_matches[:limit]
