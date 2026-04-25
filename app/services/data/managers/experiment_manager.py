from __future__ import annotations

import re
from typing import Any

from psycopg2.extras import Json

from app.core.exceptions import DatabaseError

from .base import BaseManager

THREAD_INSERT_SQL = """
INSERT INTO experiment_threads (
    mode,
    title,
    metadata,
    created_by_user_id
)
VALUES (%s, %s, %s, %s)
RETURNING
    id,
    mode,
    title,
    metadata,
    created_by_user_id,
    created_at,
    updated_at
"""

THREAD_OWNER_SCOPE_SQL = """
(
    (%s IS NULL AND t.created_by_user_id IS NULL)
    OR t.created_by_user_id = %s
)
"""

THREAD_GET_SQL = """
SELECT
    t.id,
    t.mode,
    t.title,
    t.metadata,
    t.created_by_user_id,
    t.created_at,
    t.updated_at
FROM experiment_threads t
WHERE t.id = %s
  AND """
THREAD_GET_SQL += THREAD_OWNER_SCOPE_SQL

THREAD_EXISTS_SQL = """
SELECT 1
FROM experiment_threads t
WHERE t.id = %s
  AND """
THREAD_EXISTS_SQL += THREAD_OWNER_SCOPE_SQL

THREAD_CONTEXT_GET_SQL = """
SELECT ecr.recipe_id
FROM experiment_context_recipes ecr
JOIN experiment_threads t ON t.id = ecr.thread_id
JOIN recipes r ON r.id = ecr.recipe_id
WHERE ecr.thread_id = %s
  AND """
THREAD_CONTEXT_GET_SQL += THREAD_OWNER_SCOPE_SQL
THREAD_CONTEXT_GET_SQL += """
  AND (%s OR COALESCE(r.is_test_data, FALSE) = FALSE)
ORDER BY ecr.added_at, ecr.recipe_id
"""

THREAD_CONTEXT_INSERT_SQL = """
INSERT INTO experiment_context_recipes (thread_id, recipe_id)
VALUES (%s, %s)
ON CONFLICT (thread_id, recipe_id) DO NOTHING
"""

THREAD_CONTEXT_DELETE_SQL = """
DELETE FROM experiment_context_recipes
WHERE thread_id = %s
"""

MESSAGE_NEXT_SEQUENCE_SQL = """
SELECT COALESCE(MAX(sequence_no), 0) + 1 AS next_sequence
FROM experiment_messages em
JOIN experiment_threads t ON t.id = em.thread_id
WHERE em.thread_id = %s
  AND """
MESSAGE_NEXT_SEQUENCE_SQL += THREAD_OWNER_SCOPE_SQL

MESSAGE_INSERT_SQL = """
INSERT INTO experiment_messages (
    thread_id,
    sequence_no,
    role,
    content,
    tool_name,
    tool_call
)
VALUES (%s, %s, %s, %s, %s, %s)
RETURNING
    id,
    thread_id,
    sequence_no,
    role,
    content,
    tool_name,
    tool_call,
    created_at
"""

MESSAGES_GET_SQL = """
SELECT
    em.id,
    em.thread_id,
    em.sequence_no,
    em.role,
    em.content,
    em.tool_name,
    em.tool_call,
    em.created_at
FROM experiment_messages em
JOIN experiment_threads t ON t.id = em.thread_id
WHERE em.thread_id = %s
  AND """
MESSAGES_GET_SQL += THREAD_OWNER_SCOPE_SQL
MESSAGES_GET_SQL += """
ORDER BY em.sequence_no DESC
LIMIT %s
"""

THREADS_LIST_SQL = """
SELECT
    t.id,
    t.mode,
    t.title,
    t.metadata,
    t.created_by_user_id,
    t.created_at,
    t.updated_at,
    m.role AS last_message_role,
    m.content AS last_message_content,
    m.created_at AS last_message_created_at
FROM experiment_threads t
LEFT JOIN LATERAL (
    SELECT role, content, created_at
    FROM experiment_messages
    WHERE thread_id = t.id
    ORDER BY sequence_no DESC
    LIMIT 1
) m ON true
WHERE """
THREADS_LIST_SQL += THREAD_OWNER_SCOPE_SQL
THREADS_LIST_SQL += """
ORDER BY t.updated_at DESC, t.created_at DESC
LIMIT %s
"""

THREAD_TITLE_UPDATE_IF_EMPTY_SQL = """
UPDATE experiment_threads t
SET title = %s
WHERE t.id = %s
  AND """
THREAD_TITLE_UPDATE_IF_EMPTY_SQL += THREAD_OWNER_SCOPE_SQL
THREAD_TITLE_UPDATE_IF_EMPTY_SQL += """
  AND (t.title IS NULL OR btrim(t.title) = '')
"""

THREAD_TOUCH_SQL = """
UPDATE experiment_threads t
SET updated_at = NOW()
WHERE t.id = %s
  AND """
THREAD_TOUCH_SQL += THREAD_OWNER_SCOPE_SQL

TEST_THREAD_TITLE_PATTERN = re.compile(
    r"\b("
    r"e2e|pytest|playwright|cypress|"
    r"integration[-_\s]?test|smoke[-_\s]?test"
    r")\b",
    re.IGNORECASE,
)
TEST_METADATA_FLAG_KEYS = (
    "is_test",
    "isTest",
    "test",
    "is_e2e",
    "e2e",
)
TEST_METADATA_SOURCE_KEYS = (
    "source",
    "origin",
    "env",
    "environment",
    "category",
    "tag",
    "type",
)
TEST_METADATA_SOURCE_VALUES = {
    "test",
    "e2e",
    "pytest",
    "playwright",
    "cypress",
    "integration-test",
    "integration_test",
    "smoke-test",
    "smoke_test",
    "ci",
}
TRUTHY_FLAG_VALUES = {"1", "true", "yes", "y", "on"}


class ExperimentManager(BaseManager):
    @staticmethod
    def _serialize_thread(row: dict) -> dict:
        return {
            "id": str(row["id"]),
            "mode": row["mode"],
            "title": row["title"],
            "metadata": row.get("metadata") or {},
            "created_by_user_id": (
                str(row["created_by_user_id"])
                if row.get("created_by_user_id") is not None
                else None
            ),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _serialize_message(row: dict) -> dict:
        return {
            "id": str(row["id"]),
            "thread_id": str(row["thread_id"]),
            "sequence_no": row["sequence_no"],
            "role": row["role"],
            "content": row["content"],
            "tool_name": row.get("tool_name"),
            "tool_call": row.get("tool_call"),
            "created_at": row["created_at"],
        }

    @staticmethod
    def _normalize_context_recipe_ids(context_recipe_ids: list[str]) -> list[str]:
        seen = set()
        ordered_ids: list[str] = []
        for recipe_id in context_recipe_ids:
            normalized = str(recipe_id).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            ordered_ids.append(normalized)
        return ordered_ids

    @staticmethod
    def _is_truthy_flag(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value == 1
        if isinstance(value, str):
            return value.strip().lower() in TRUTHY_FLAG_VALUES
        return False

    @classmethod
    def _is_test_thread(cls, thread: dict) -> bool:
        metadata = thread.get("metadata")
        if isinstance(metadata, dict):
            for key in TEST_METADATA_FLAG_KEYS:
                if cls._is_truthy_flag(metadata.get(key)):
                    return True
            for key in TEST_METADATA_SOURCE_KEYS:
                value = metadata.get(key)
                if (
                    isinstance(value, str)
                    and value.strip().lower() in TEST_METADATA_SOURCE_VALUES
                ):
                    return True

        title = thread.get("title")
        return isinstance(title, str) and bool(TEST_THREAD_TITLE_PATTERN.search(title))

    @staticmethod
    def _owner_scope_params(viewer_user_id: str | None) -> tuple[str | None, str | None]:
        return (viewer_user_id, viewer_user_id)

    def _thread_exists(
        self,
        cursor,
        thread_id: str,
        viewer_user_id: str | None = None,
    ) -> bool:
        cursor.execute(
            THREAD_EXISTS_SQL,
            (thread_id, *self._owner_scope_params(viewer_user_id)),
        )
        return cursor.fetchone() is not None

    def _replace_context_recipes(
        self, cursor, thread_id: str, context_recipe_ids: list[str]
    ) -> list[str]:
        normalized_ids = self._normalize_context_recipe_ids(context_recipe_ids)
        cursor.execute(THREAD_CONTEXT_DELETE_SQL, (thread_id,))
        for recipe_id in normalized_ids:
            cursor.execute(THREAD_CONTEXT_INSERT_SQL, (thread_id, recipe_id))
        return normalized_ids

    def get_context_recipe_ids(
        self,
        thread_id: str,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> list[str]:
        try:
            with self.get_db_context() as (_conn, cursor):
                cursor.execute(
                    THREAD_CONTEXT_GET_SQL,
                    (
                        thread_id,
                        *self._owner_scope_params(viewer_user_id),
                        include_test_data,
                    ),
                )
                rows = cursor.fetchall()
                return [str(row["recipe_id"]) for row in rows]
        except Exception as e:
            raise DatabaseError(f"Failed to get thread context recipes: {e!s}") from e

    def create_thread(
        self,
        mode: str,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        context_recipe_ids: list[str] | None = None,
        created_by_user_id: str | None = None,
    ) -> dict:
        normalized_context = self._normalize_context_recipe_ids(
            context_recipe_ids or []
        )
        metadata_payload = metadata if isinstance(metadata, dict) else {}
        try:
            with self.get_db_context() as (_conn, cursor):
                cursor.execute(
                    THREAD_INSERT_SQL,
                    (mode, title, Json(metadata_payload), created_by_user_id),
                )
                row = cursor.fetchone()
                if row is None:
                    raise DatabaseError("Thread insertion returned no row")

                thread = self._serialize_thread(dict(row))
                thread_id = thread["id"]
                if normalized_context:
                    self._replace_context_recipes(
                        cursor=cursor,
                        thread_id=thread_id,
                        context_recipe_ids=normalized_context,
                    )
                thread["context_recipe_ids"] = normalized_context
                return thread
        except Exception as e:
            raise DatabaseError(f"Failed to create experiment thread: {e!s}") from e

    def get_thread(
        self,
        thread_id: str,
        message_limit: int = 100,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> dict | None:
        query_limit = max(1, min(int(message_limit), 500))
        try:
            with self.get_db_context() as (_conn, cursor):
                cursor.execute(
                    THREAD_GET_SQL,
                    (thread_id, *self._owner_scope_params(viewer_user_id)),
                )
                row = cursor.fetchone()
                if row is None:
                    return None

                thread = self._serialize_thread(dict(row))
                cursor.execute(
                    THREAD_CONTEXT_GET_SQL,
                    (
                        thread_id,
                        *self._owner_scope_params(viewer_user_id),
                        include_test_data,
                    ),
                )
                context_rows = cursor.fetchall()
                thread["context_recipe_ids"] = [
                    str(context_row["recipe_id"]) for context_row in context_rows
                ]

                cursor.execute(
                    MESSAGES_GET_SQL,
                    (
                        thread_id,
                        *self._owner_scope_params(viewer_user_id),
                        query_limit,
                    ),
                )
                message_rows = cursor.fetchall()
                # Query fetches latest messages first for limit efficiency.
                messages = [
                    self._serialize_message(dict(item)) for item in message_rows
                ]
                thread["messages"] = list(reversed(messages))
                return thread
        except Exception as e:
            raise DatabaseError(f"Failed to load experiment thread: {e!s}") from e

    def set_context_recipe_ids(
        self,
        thread_id: str,
        context_recipe_ids: list[str],
        viewer_user_id: str | None = None,
    ) -> bool:
        try:
            with self.get_db_context() as (_conn, cursor):
                if not self._thread_exists(cursor, thread_id, viewer_user_id):
                    return False
                self._replace_context_recipes(cursor, thread_id, context_recipe_ids)
                return True
        except Exception as e:
            raise DatabaseError(
                f"Failed to update thread context recipes: {e!s}"
            ) from e

    def list_messages(
        self,
        thread_id: str,
        limit: int = 100,
        viewer_user_id: str | None = None,
    ) -> list[dict]:
        query_limit = max(1, min(int(limit), 500))
        try:
            with self.get_db_context() as (_conn, cursor):
                cursor.execute(
                    MESSAGES_GET_SQL,
                    (
                        thread_id,
                        *self._owner_scope_params(viewer_user_id),
                        query_limit,
                    ),
                )
                rows = cursor.fetchall()
                messages = [self._serialize_message(dict(item)) for item in rows]
                return list(reversed(messages))
        except Exception as e:
            raise DatabaseError(f"Failed to list experiment messages: {e!s}") from e

    def create_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        tool_name: str | None = None,
        tool_call: dict[str, Any] | None = None,
        viewer_user_id: str | None = None,
    ) -> dict | None:
        normalized_content = content.strip()
        if not normalized_content:
            raise ValueError("Message content cannot be blank")

        try:
            with self.get_db_context() as (_conn, cursor):
                if not self._thread_exists(cursor, thread_id, viewer_user_id):
                    return None

                cursor.execute(
                    MESSAGE_NEXT_SEQUENCE_SQL,
                    (thread_id, *self._owner_scope_params(viewer_user_id)),
                )
                sequence_row = cursor.fetchone()
                if not sequence_row:
                    raise DatabaseError("Unable to compute next message sequence")
                next_sequence = int(sequence_row["next_sequence"])

                tool_call_payload = (
                    Json(tool_call) if isinstance(tool_call, dict) else None
                )
                cursor.execute(
                    MESSAGE_INSERT_SQL,
                    (
                        thread_id,
                        next_sequence,
                        role,
                        normalized_content,
                        tool_name,
                        tool_call_payload,
                    ),
                )
                row = cursor.fetchone()
                if row is None:
                    raise DatabaseError("Message insertion returned no row")
                cursor.execute(
                    THREAD_TOUCH_SQL,
                    (thread_id, *self._owner_scope_params(viewer_user_id)),
                )
                return self._serialize_message(dict(row))
        except Exception as e:
            raise DatabaseError(f"Failed to create experiment message: {e!s}") from e

    def set_thread_title_if_empty(
        self,
        thread_id: str,
        title: str,
        viewer_user_id: str | None = None,
    ) -> bool:
        normalized_title = title.strip()
        if not normalized_title:
            return False
        try:
            with self.get_db_context() as (_conn, cursor):
                cursor.execute(
                    THREAD_TITLE_UPDATE_IF_EMPTY_SQL,
                    (
                        normalized_title,
                        thread_id,
                        *self._owner_scope_params(viewer_user_id),
                    ),
                )
                return cursor.rowcount > 0
        except Exception as e:
            raise DatabaseError(f"Failed to update thread title: {e!s}") from e

    def list_threads(
        self,
        limit: int = 20,
        include_test: bool = False,
        viewer_user_id: str | None = None,
    ) -> list[dict]:
        query_limit = max(1, min(int(limit), 100))
        fetch_limit = query_limit if include_test else 500
        try:
            with self.get_db_context() as (_conn, cursor):
                cursor.execute(
                    THREADS_LIST_SQL,
                    (*self._owner_scope_params(viewer_user_id), fetch_limit),
                )
                rows = cursor.fetchall()
                threads: list[dict] = []
                for row in rows:
                    thread = self._serialize_thread(dict(row))
                    thread["last_message_role"] = row.get("last_message_role")
                    thread["last_message_content"] = row.get("last_message_content")
                    thread["last_message_created_at"] = row.get(
                        "last_message_created_at"
                    )
                    threads.append(thread)
                if include_test:
                    return threads[:query_limit]

                filtered_threads = [
                    thread for thread in threads if not self._is_test_thread(thread)
                ]
                return filtered_threads[:query_limit]
        except Exception as e:
            raise DatabaseError(f"Failed to list experiment threads: {e!s}") from e
