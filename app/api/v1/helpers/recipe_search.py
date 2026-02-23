import re

from app.core.logging import get_logger

logger = get_logger(__name__)

WRAPPING_QUOTES = {'"', "'"}
TOKEN_PATTERN = re.compile(r"[a-z]+")

CUISINE_KEYWORDS: dict[str, set[str]] = {
    "indian": {
        "indian",
        "paneer",
        "tikka",
        "masala",
        "aloo",
        "gobi",
        "chana",
        "dal",
        "garam",
        "korma",
        "vindaloo",
        "saag",
    },
    "thai": {
        "thai",
        "lemongrass",
        "galangal",
        "basil",
        "coconut",
        "kaffir",
        "krapow",
        "tom",
        "yum",
    },
    "italian": {
        "italian",
        "pasta",
        "lasagna",
        "spaghetti",
        "penne",
        "risotto",
        "parmesan",
        "pecorino",
    },
    "japanese": {"japanese", "udon", "ramen", "miso", "dashi", "teriyaki"},
}

CURRY_FAMILY_KEYWORDS = {
    "curry",
    "masala",
    "korma",
    "vindaloo",
    "saag",
    "aloo",
    "gobi",
    "chana",
    "tikka",
    "dal",
}


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


def _tokenize(value: object) -> set[str]:
    if value is None:
        return set()
    return set(TOKEN_PATTERN.findall(str(value).lower()))


def _infer_cuisines(tokens: set[str]) -> set[str]:
    matched: set[str] = set()
    for cuisine, cuisine_tokens in CUISINE_KEYWORDS.items():
        if tokens & cuisine_tokens:
            matched.add(cuisine)
    return matched


def _curry_intent(tokens: set[str]) -> bool:
    return bool(tokens & CURRY_FAMILY_KEYWORDS)


def _compute_boosts(
    query: str | None,
    candidate_name: object,
    cuisine_boost: float,
    family_boost: float,
) -> tuple[float, float, float]:
    if not query:
        return 0.0, 0.0, 0.0

    query_tokens = _tokenize(query)
    candidate_tokens = _tokenize(candidate_name)
    if not query_tokens or not candidate_tokens:
        return 0.0, 0.0, 0.0

    applied_cuisine_boost = 0.0
    query_cuisines = _infer_cuisines(query_tokens)
    candidate_cuisines = _infer_cuisines(candidate_tokens)
    if query_cuisines and candidate_cuisines and query_cuisines & candidate_cuisines:
        applied_cuisine_boost = max(cuisine_boost, 0.0)

    applied_family_boost = 0.0
    if _curry_intent(query_tokens) and _curry_intent(candidate_tokens):
        applied_family_boost = max(family_boost, 0.0)

    total_boost = applied_cuisine_boost + applied_family_boost
    return total_boost, applied_cuisine_boost, applied_family_boost


def _rank_matches(
    matches: list[dict],
    ranked_items: list[dict],
    min_rerank_score: float,
    rerank_weight: float,
    query: str | None = None,
    cuisine_boost: float = 0.0,
    family_boost: float = 0.0,
    rerank_mode: str | None = None,
) -> tuple[list[dict], bool]:
    match_by_id = {}
    for item in matches:
        recipe_id = _normalize_recipe_id(item.get("id"))
        if recipe_id is not None:
            match_by_id[recipe_id] = item

    ranked_ids_found = False
    normalized_min_score = min(max(min_rerank_score, 0.0), 1.0)
    normalized_rerank_weight = min(max(rerank_weight, 0.0), 1.0)

    ordered_matches: list[dict] = []
    used_ids: set[str] = set()
    for ranked in ranked_items:
        recipe_id = _normalize_recipe_id(ranked.get("id"))
        if recipe_id is None or recipe_id in used_ids or recipe_id not in match_by_id:
            continue
        ranked_ids_found = True

        raw_rerank_score = _to_float(ranked.get("score"))
        if raw_rerank_score is None:
            continue

        total_boost, applied_cuisine_boost, applied_family_boost = _compute_boosts(
            query=query,
            candidate_name=match_by_id[recipe_id].get("name"),
            cuisine_boost=cuisine_boost,
            family_boost=family_boost,
        )
        rerank_score = min(max(raw_rerank_score + total_boost, 0.0), 1.0)
        if rerank_score < normalized_min_score:
            continue

        row = dict(match_by_id[recipe_id])
        embedding_score = _embedding_score_from_distance(row.get("distance"))
        combined_score = (normalized_rerank_weight * rerank_score) + (
            (1.0 - normalized_rerank_weight) * embedding_score
        )
        row["rerank_score"] = rerank_score
        row["embedding_score"] = embedding_score
        row["combined_score"] = combined_score
        if rerank_score != raw_rerank_score:
            row["raw_rerank_score"] = raw_rerank_score
        if applied_cuisine_boost > 0.0:
            row["cuisine_boost"] = applied_cuisine_boost
        if applied_family_boost > 0.0:
            row["family_boost"] = applied_family_boost
        if rerank_mode:
            row["rerank_mode"] = rerank_mode
        ordered_matches.append(row)
        used_ids.add(recipe_id)

    ordered_matches.sort(key=lambda item: item.get("combined_score", 0.0), reverse=True)
    return ordered_matches, ranked_ids_found


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
    fallback_min_rerank_score: float | None = 0.25,
    rerank_weight: float = 0.70,
    query: str | None = None,
    cuisine_boost: float = 0.0,
    family_boost: float = 0.0,
) -> list[dict]:
    if not ranked_items:
        return matches[:limit]

    strict_matches, ranked_ids_found = _rank_matches(
        matches=matches,
        ranked_items=ranked_items,
        min_rerank_score=min_rerank_score,
        rerank_weight=rerank_weight,
    )
    if not ranked_ids_found:
        return matches[:limit]
    if strict_matches:
        return strict_matches[:limit]

    normalized_fallback_min = (
        None
        if fallback_min_rerank_score is None
        else min(max(fallback_min_rerank_score, 0.0), 1.0)
    )
    if normalized_fallback_min is None:
        return []
    if normalized_fallback_min >= min(max(min_rerank_score, 0.0), 1.0):
        return []

    fallback_matches, _ = _rank_matches(
        matches=matches,
        ranked_items=ranked_items,
        min_rerank_score=normalized_fallback_min,
        rerank_weight=rerank_weight,
        query=query,
        cuisine_boost=cuisine_boost,
        family_boost=family_boost,
        rerank_mode="fallback",
    )
    return fallback_matches[:limit]
