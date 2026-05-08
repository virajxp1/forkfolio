import uuid
from datetime import datetime
from typing import Optional

from app.api.schemas import Recipe
from app.core.exceptions import DatabaseError

from .base import BaseManager

RECIPE_WITH_CHILDREN_SQL = """
SELECT r.*,
    COALESCE(i.ingredients, ARRAY[]::text[]) AS ingredients,
    COALESCE(s.instructions, ARRAY[]::text[]) AS instructions
FROM recipes r
LEFT JOIN LATERAL (
    SELECT array_agg(ingredient_text ORDER BY order_index) AS ingredients
    FROM recipe_ingredients
    WHERE recipe_id = r.id
) i ON true
LEFT JOIN LATERAL (
    SELECT array_agg(instruction_text ORDER BY step_number) AS instructions
    FROM recipe_instructions
    WHERE recipe_id = r.id
) s ON true
WHERE r.id = %s
  AND (%s OR COALESCE(r.is_test_data, FALSE) = FALSE)
  AND (COALESCE(r.is_public, TRUE) = TRUE OR r.created_by_user_id = %s::uuid)
"""
EMBEDDINGS_SELECT_SQL = """
SELECT id, embedding_type, embedding, created_at
FROM recipe_embeddings
WHERE recipe_id = %s
ORDER BY created_at
"""
HYBRID_RECIPES_SQL = """
WITH visible_recipes AS (
    SELECT r.id, r.title, r.created_at
    FROM recipes r
    WHERE (%s OR COALESCE(r.is_test_data, FALSE) = FALSE)
      AND (COALESCE(r.is_public, TRUE) = TRUE OR r.created_by_user_id = %s::uuid)
),
query_params AS (
    SELECT
        websearch_to_tsquery('english', %s) AS tsquery,
        lower(%s) AS trigram_query
),
ingredient_scores AS (
    -- Pre-filter ingredients via FTS or trigram operators so the GIN indexes
    -- on recipe_ingredients can prune rows before aggregation. Recipes whose
    -- ingredients all fall out join into `scored` with NULL scores below.
    SELECT
        ri.recipe_id,
        MAX(
            ts_rank_cd(
                to_tsvector('english', COALESCE(ri.ingredient_text, '')),
                qp.tsquery,
                32
            )
        ) AS ingredient_fts_score,
        MAX(
            word_similarity(
                qp.trigram_query,
                lower(COALESCE(ri.ingredient_text, ''))
            )
        ) AS ingredient_trigram_score
    FROM recipe_ingredients ri
    JOIN visible_recipes vr ON vr.id = ri.recipe_id
    CROSS JOIN query_params qp
    WHERE to_tsvector('english', COALESCE(ri.ingredient_text, '')) @@ qp.tsquery
       OR lower(COALESCE(ri.ingredient_text, '')) %% qp.trigram_query
    GROUP BY ri.recipe_id
),
scored AS (
    SELECT
        vr.id AS recipe_id,
        vr.title AS recipe_name,
        vr.created_at AS recipe_created_at,
        -- pgvector's <=> returns cosine distance in [0, 2]; clamping to [0, 1]
        -- keeps vector_score = 1 - distance in [0, 1] alongside the lexical
        -- scores. Distances above 1.0 fold to vector_score = 0 by design.
        e.embedding <=> %s::vector AS raw_distance,
        ts_rank_cd(
            to_tsvector('english', COALESCE(vr.title, '')),
            qp.tsquery,
            32
        ) AS title_fts_score,
        word_similarity(
            qp.trigram_query,
            lower(COALESCE(vr.title, ''))
        ) AS title_trigram_score,
        COALESCE(ingredient_scores.ingredient_fts_score, 0.0) AS ingredient_fts_score,
        COALESCE(
            ingredient_scores.ingredient_trigram_score,
            0.0
        ) AS ingredient_trigram_score
    FROM visible_recipes vr
    JOIN recipe_embeddings e
      ON e.recipe_id = vr.id
     AND e.embedding_type = %s
    CROSS JOIN query_params qp
    LEFT JOIN ingredient_scores ON ingredient_scores.recipe_id = vr.id
),
ranked AS (
    SELECT
        recipe_id,
        recipe_name,
        recipe_created_at,
        LEAST(GREATEST(raw_distance, 0.0), 1.0) AS distance,
        GREATEST(title_fts_score, ingredient_fts_score) AS fts_score,
        GREATEST(title_trigram_score, ingredient_trigram_score) AS trigram_score,
        LEAST(GREATEST(1.0 - raw_distance, 0.0), 1.0) AS vector_score
    FROM scored
),
final AS (
    SELECT
        recipe_id,
        recipe_name,
        recipe_created_at,
        distance,
        fts_score,
        trigram_score,
        vector_score,
        ((%s * fts_score) + (%s * trigram_score) + (%s * vector_score))
            AS combined_score
    FROM ranked
)
SELECT
    recipe_id,
    recipe_name,
    recipe_created_at,
    distance,
    fts_score,
    trigram_score,
    vector_score,
    combined_score
FROM final
WHERE (
    distance <= %s
    OR fts_score > 0.0
    OR trigram_score >= %s
)
AND combined_score >= %s
ORDER BY combined_score DESC, fts_score DESC, trigram_score DESC, distance ASC, recipe_name ASC
LIMIT %s
"""
INGREDIENTS_FOR_RECIPES_SQL = """
SELECT ri.recipe_id, ri.ingredient_text
FROM recipe_ingredients ri
JOIN recipes r ON r.id = ri.recipe_id
WHERE ri.recipe_id = ANY(%s::uuid[])
  AND (%s OR COALESCE(r.is_test_data, FALSE) = FALSE)
  AND (COALESCE(r.is_public, TRUE) = TRUE OR r.created_by_user_id = %s::uuid)
ORDER BY ri.recipe_id, ri.order_index
"""
ALL_INGREDIENTS_FOR_RECIPES_SQL = """
SELECT
    r.id AS recipe_id,
    COALESCE(
        array_agg(i.ingredient_text ORDER BY i.order_index)
            FILTER (WHERE i.ingredient_text IS NOT NULL),
        ARRAY[]::text[]
    ) AS ingredients
FROM recipes r
LEFT JOIN recipe_ingredients i ON i.recipe_id = r.id
WHERE r.id = ANY(%s::uuid[])
  AND (%s OR COALESCE(r.is_test_data, FALSE) = FALSE)
  AND (COALESCE(r.is_public, TRUE) = TRUE OR r.created_by_user_id = %s::uuid)
GROUP BY r.id
"""
RECIPES_PAGE_SQL = """
SELECT
    r.id,
    r.title,
    r.servings,
    r.total_time,
    r.source_url,
    r.is_public,
    r.created_by_user_id,
    r.is_test_data,
    r.created_at,
    r.updated_at
FROM recipes r
WHERE (%s OR COALESCE(r.is_test_data, FALSE) = FALSE)
  AND (COALESCE(r.is_public, TRUE) = TRUE OR r.created_by_user_id = %s::uuid)
ORDER BY r.created_at DESC, r.id DESC
LIMIT %s
"""
RECIPES_PAGE_WITH_CURSOR_SQL = """
SELECT
    r.id,
    r.title,
    r.servings,
    r.total_time,
    r.source_url,
    r.is_public,
    r.created_by_user_id,
    r.is_test_data,
    r.created_at,
    r.updated_at
FROM recipes r
WHERE (r.created_at, r.id) < (%s::timestamp, %s::uuid)
  AND (%s OR COALESCE(r.is_test_data, FALSE) = FALSE)
  AND (COALESCE(r.is_public, TRUE) = TRUE OR r.created_by_user_id = %s::uuid)
ORDER BY r.created_at DESC, r.id DESC
LIMIT %s
"""
RECIPE_BY_EXACT_TITLE_SQL = """
SELECT r.id, r.title, r.created_at
FROM recipes r
WHERE lower(r.title) = lower(%s)
  AND (%s OR COALESCE(r.is_test_data, FALSE) = FALSE)
  AND (COALESCE(r.is_public, TRUE) = TRUE OR r.created_by_user_id = %s::uuid)
ORDER BY r.created_at DESC
LIMIT 1
"""
RECIPE_BY_TITLE_PREFIX_SQL = """
SELECT r.id, r.title, r.created_at
FROM recipes r
WHERE lower(r.title) LIKE lower(%s) || '%%'
  AND (%s OR COALESCE(r.is_test_data, FALSE) = FALSE)
  AND (COALESCE(r.is_public, TRUE) = TRUE OR r.created_by_user_id = %s::uuid)
ORDER BY char_length(r.title) ASC, r.created_at DESC
LIMIT 1
"""


class RecipeManager(BaseManager):
    @staticmethod
    def _generate_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def _normalize_embedding_value(embedding_value):
        if embedding_value is None:
            return None
        if hasattr(embedding_value, "tolist"):
            return embedding_value.tolist()
        try:
            return list(embedding_value)
        except TypeError:
            return embedding_value

    def _insert_recipe(
        self,
        cursor,
        recipe_id: str,
        title: str,
        servings: Optional[str],
        total_time: Optional[str],
        is_test_data: bool = False,
        source_url: Optional[str] = None,
        is_public: bool = True,
        created_by_user_id: str | None = None,
    ) -> None:
        sql = """
        INSERT INTO recipes (
            id,
            title,
            servings,
            total_time,
            source_url,
            is_public,
            created_by_user_id,
            is_test_data
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(
            sql,
            (
                recipe_id,
                title,
                servings,
                total_time,
                source_url,
                is_public,
                created_by_user_id,
                is_test_data,
            ),
        )

    def _insert_ingredients(
        self, cursor, recipe_id: str, ingredients: list[str]
    ) -> None:
        sql = """
        INSERT INTO recipe_ingredients (
            id, recipe_id, ingredient_text, order_index
        )
        VALUES (%s, %s, %s, %s)
        """
        for index, ingredient_text in enumerate(ingredients):
            ingredient_id = self._generate_id()
            cursor.execute(
                sql,
                (ingredient_id, recipe_id, ingredient_text, index),
            )

    def _insert_instructions(
        self, cursor, recipe_id: str, instructions: list[str]
    ) -> None:
        sql = """
        INSERT INTO recipe_instructions (
            id, recipe_id, instruction_text, step_number
        )
        VALUES (%s, %s, %s, %s)
        """
        for step_num, instruction_text in enumerate(instructions, 1):
            instruction_id = self._generate_id()
            cursor.execute(
                sql,
                (instruction_id, recipe_id, instruction_text, step_num),
            )

    def _insert_embedding(
        self,
        cursor,
        recipe_id: str,
        embedding_type: str,
        embedding: list[float],
    ) -> None:
        sql = """
        INSERT INTO recipe_embeddings (id, recipe_id, embedding_type, embedding)
        VALUES (%s, %s, %s, %s)
        """
        embedding_id = self._generate_id()
        cursor.execute(sql, (embedding_id, recipe_id, embedding_type, embedding))

    def _fetch_recipe_with_children(
        self,
        cursor,
        recipe_id: str,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> Optional[dict]:
        cursor.execute(
            RECIPE_WITH_CHILDREN_SQL,
            (recipe_id, include_test_data, viewer_user_id),
        )
        row = cursor.fetchone()
        if not row:
            return None
        recipe_data = dict(row)
        recipe_data["ingredients"] = list(recipe_data.get("ingredients") or [])
        recipe_data["instructions"] = list(recipe_data.get("instructions") or [])
        return recipe_data

    def _fetch_embeddings(self, cursor, recipe_id: str) -> list[dict]:
        cursor.execute(EMBEDDINGS_SELECT_SQL, (recipe_id,))
        embeddings = [dict(row) for row in cursor.fetchall()]
        for row in embeddings:
            row["embedding"] = self._normalize_embedding_value(row.get("embedding"))
        return embeddings

    @staticmethod
    def _format_semantic_search_row(row: dict) -> dict:
        recipe_id = row.get("recipe_id")
        distance_value = row.get("distance")
        distance = float(distance_value) if distance_value is not None else None
        formatted = {
            "id": str(recipe_id) if recipe_id is not None else None,
            "name": row.get("recipe_name"),
            "distance": distance,
        }
        created_at = row.get("recipe_created_at")
        if created_at is not None:
            formatted["created_at"] = created_at
        for key in ("combined_score", "fts_score", "trigram_score", "vector_score"):
            value = row.get(key)
            if value is not None:
                formatted[key] = float(value)
        return formatted

    @staticmethod
    def _format_recipe_metadata_row(row: dict) -> dict:
        return {
            "id": str(row["id"]),
            "title": row.get("title"),
            "created_at": row.get("created_at"),
        }

    def delete_recipe(self, recipe_id: str) -> bool:
        """Delete a recipe by ID"""
        try:
            with self.get_db_context() as (_conn, cursor):
                sql = "DELETE FROM recipes WHERE id = %s"
                cursor.execute(sql, (recipe_id,))
                return cursor.rowcount > 0
        except Exception as e:
            raise DatabaseError(f"Failed to delete recipe: {e!s}") from e

    def create_recipe_from_model(
        self,
        recipe: Recipe,
        source_url: Optional[str] = None,
        embedding_type: Optional[str] = None,
        embedding: Optional[list[float]] = None,
        is_test_data: bool = False,
        is_public: bool = True,
        created_by_user_id: str | None = None,
    ) -> str:
        """Create recipe from a model with ingredients, instructions, and embeddings."""
        recipe_id = self._generate_id()

        try:
            with self.get_db_context() as (_conn, cursor):
                self._insert_recipe(
                    cursor=cursor,
                    recipe_id=recipe_id,
                    title=recipe.title,
                    servings=recipe.servings,
                    total_time=recipe.total_time,
                    source_url=source_url,
                    is_public=is_public,
                    created_by_user_id=created_by_user_id,
                    is_test_data=is_test_data,
                )
                self._insert_ingredients(cursor, recipe_id, recipe.ingredients)
                self._insert_instructions(cursor, recipe_id, recipe.instructions)

                if embedding_type and embedding is not None:
                    self._insert_embedding(
                        cursor=cursor,
                        recipe_id=recipe_id,
                        embedding_type=embedding_type,
                        embedding=embedding,
                    )

                return recipe_id

        except Exception as e:
            raise DatabaseError(f"Failed to create recipe: {e!s}") from e

    def get_recipe_metadata(
        self,
        recipe_id: str,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> Optional[dict]:
        """Get minimal recipe metadata (id, title, created_at) without children."""
        try:
            with self.get_db_context() as (_conn, cursor):
                cursor.execute(
                    """
                    SELECT id, title, created_at
                    FROM recipes
                    WHERE id = %s
                      AND (%s OR COALESCE(is_test_data, FALSE) = FALSE)
                      AND (COALESCE(is_public, TRUE) = TRUE OR created_by_user_id = %s::uuid)
                    """,
                    (recipe_id, include_test_data, viewer_user_id),
                )
                row = cursor.fetchone()
                return self._format_recipe_metadata_row(dict(row)) if row else None
        except Exception as e:
            raise DatabaseError(f"Failed to get recipe metadata: {e!s}") from e

    def get_full_recipe(
        self,
        recipe_id: str,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> Optional[dict]:
        """Get a complete recipe with ingredients and instructions"""
        try:
            with self.get_db_context() as (_conn, cursor):
                recipe_data = self._fetch_recipe_with_children(
                    cursor=cursor,
                    recipe_id=recipe_id,
                    include_test_data=include_test_data,
                    viewer_user_id=viewer_user_id,
                )
                if not recipe_data:
                    return None
                return recipe_data

        except Exception as e:
            raise DatabaseError(f"Failed to get recipe: {e!s}") from e

    def get_full_recipe_with_embeddings(
        self,
        recipe_id: str,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> Optional[dict]:
        """Get a complete recipe with ingredients, instructions, and embeddings."""
        try:
            with self.get_db_context() as (_conn, cursor):
                recipe_data = self._fetch_recipe_with_children(
                    cursor=cursor,
                    recipe_id=recipe_id,
                    include_test_data=include_test_data,
                    viewer_user_id=viewer_user_id,
                )
                if not recipe_data:
                    return None

                recipe_data["embeddings"] = self._fetch_embeddings(cursor, recipe_id)
                return recipe_data

        except Exception as e:
            raise DatabaseError(f"Failed to get recipe with embeddings: {e!s}") from e

    def list_recipes_page(
        self,
        limit: int = 50,
        cursor_created_at: datetime | None = None,
        cursor_id: str | None = None,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> list[dict]:
        """List recipes ordered by newest first with optional cursor pagination."""
        query_limit = max(1, int(limit))
        try:
            with self.get_db_context() as (_conn, cursor):
                if cursor_created_at is not None and cursor_id is not None:
                    cursor.execute(
                        RECIPES_PAGE_WITH_CURSOR_SQL,
                        (
                            cursor_created_at,
                            cursor_id,
                            include_test_data,
                            viewer_user_id,
                            query_limit,
                        ),
                    )
                else:
                    cursor.execute(
                        RECIPES_PAGE_SQL,
                        (include_test_data, viewer_user_id, query_limit),
                    )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            raise DatabaseError(f"Failed to list recipes: {e!s}") from e

    def get_ingredient_previews(
        self,
        recipe_ids: list[str],
        max_ingredients: int = 8,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> dict[str, list[str]]:
        """
        Fetch ingredient previews for many recipes in one query.

        Returns a mapping of recipe_id -> first N ingredient strings ordered by index.
        """
        if not recipe_ids:
            return {}

        normalized_ids: list[str] = []
        for recipe_id in recipe_ids:
            try:
                normalized_ids.append(str(uuid.UUID(str(recipe_id))))
            except (TypeError, ValueError):
                continue

        if not normalized_ids:
            return {}

        max_items = max(1, max_ingredients)
        previews: dict[str, list[str]] = {recipe_id: [] for recipe_id in normalized_ids}

        try:
            with self.get_db_context() as (_conn, cursor):
                cursor.execute(
                    INGREDIENTS_FOR_RECIPES_SQL,
                    (normalized_ids, include_test_data, viewer_user_id),
                )
                for row in cursor.fetchall():
                    recipe_id = str(row["recipe_id"])
                    ingredient = row["ingredient_text"]
                    bucket = previews.setdefault(recipe_id, [])
                    if len(bucket) < max_items and ingredient is not None:
                        bucket.append(ingredient)
            return previews
        except Exception as e:
            raise DatabaseError(f"Failed to get ingredient previews: {e!s}") from e

    def find_recipe_by_exact_title(
        self,
        title: str,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> Optional[dict]:
        normalized = (title or "").strip()
        if not normalized:
            return None
        try:
            with self.get_db_context() as (_conn, cursor):
                cursor.execute(
                    RECIPE_BY_EXACT_TITLE_SQL,
                    (normalized, include_test_data, viewer_user_id),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return self._format_recipe_metadata_row(dict(row))
        except Exception as e:
            raise DatabaseError(f"Failed to find recipe by exact title: {e!s}") from e

    def find_recipe_by_title_prefix(
        self,
        title_prefix: str,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> Optional[dict]:
        normalized = (title_prefix or "").strip()
        if not normalized:
            return None
        try:
            with self.get_db_context() as (_conn, cursor):
                cursor.execute(
                    RECIPE_BY_TITLE_PREFIX_SQL,
                    (normalized, include_test_data, viewer_user_id),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return self._format_recipe_metadata_row(dict(row))
        except Exception as e:
            raise DatabaseError(f"Failed to find recipe by title prefix: {e!s}") from e

    def get_ingredients_for_recipes(
        self,
        recipe_ids: list[str],
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> dict[str, list[str]]:
        """
        Fetch full ingredient lists for many recipes in one query.

        Returns a mapping of recipe_id -> ordered ingredient strings.
        """
        if not recipe_ids:
            return {}

        normalized_ids: list[str] = []
        for recipe_id in recipe_ids:
            try:
                normalized_id = str(uuid.UUID(str(recipe_id)))
            except (TypeError, ValueError):
                continue
            if normalized_id not in normalized_ids:
                normalized_ids.append(normalized_id)

        if not normalized_ids:
            return {}

        try:
            with self.get_db_context() as (_conn, cursor):
                cursor.execute(
                    ALL_INGREDIENTS_FOR_RECIPES_SQL,
                    (normalized_ids, include_test_data, viewer_user_id),
                )
                rows = cursor.fetchall()
                ingredients_by_recipe: dict[str, list[str]] = {}
                for row in rows:
                    row_data = dict(row)
                    ingredients_by_recipe[str(row_data["recipe_id"])] = list(
                        row_data.get("ingredients") or []
                    )
                return ingredients_by_recipe
        except Exception as e:
            raise DatabaseError(f"Failed to get ingredients for recipes: {e!s}") from e

    def search_recipes_hybrid(
        self,
        query: str,
        embedding: list[float],
        embedding_type: str,
        limit: int = 10,
        max_distance: float = 0.35,
        trigram_threshold: float = 0.18,
        min_score: float = 0.1,
        fts_weight: float = 0.45,
        trigram_weight: float = 0.2,
        vector_weight: float = 0.35,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> list[dict]:
        """Find recipes by combining lexical and semantic ranking signals."""
        try:
            with self.get_db_context() as (_conn, cursor):
                cursor.execute(
                    HYBRID_RECIPES_SQL,
                    (
                        include_test_data,
                        viewer_user_id,
                        query,
                        query,
                        embedding,
                        embedding_type,
                        fts_weight,
                        trigram_weight,
                        vector_weight,
                        max_distance,
                        trigram_threshold,
                        min_score,
                        limit,
                    ),
                )
                rows = cursor.fetchall()
                return [self._format_semantic_search_row(dict(row)) for row in rows]
        except Exception as e:
            raise DatabaseError(
                f"Failed to search recipes by hybrid ranking: {e!s}"
            ) from e

    def find_nearest_embedding(
        self,
        embedding: list[float],
        embedding_type: str,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> Optional[dict]:
        """Find the nearest embedding by cosine distance."""
        try:
            with self.get_db_context() as (_conn, cursor):
                sql = """
                SELECT
                    e.recipe_id,
                    e.embedding_type,
                    e.embedding <=> %s::vector AS distance
                FROM recipe_embeddings e
                JOIN recipes r ON r.id = e.recipe_id
                WHERE e.embedding_type = %s
                  AND (%s OR COALESCE(r.is_test_data, FALSE) = FALSE)
                  AND (COALESCE(r.is_public, TRUE) = TRUE OR r.created_by_user_id = %s::uuid)
                ORDER BY distance
                LIMIT 1
                """
                cursor.execute(
                    sql,
                    (embedding, embedding_type, include_test_data, viewer_user_id),
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            raise DatabaseError(f"Failed to find nearest embedding: {e!s}") from e
