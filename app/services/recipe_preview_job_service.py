from __future__ import annotations

import threading
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from app.core.cache import RECIPE_PREVIEW_JOB_CACHE_TTL_SECONDS, recipe_preview_job_cache
from app.core.logging import get_logger
from app.services.recipe_processing_service import RecipeProcessingService

logger = get_logger(__name__)

PREVIEW_JOB_STATUS_QUEUED = "queued"
PREVIEW_JOB_STATUS_PROCESSING = "processing"
PREVIEW_JOB_STATUS_COMPLETED = "completed"
PREVIEW_JOB_STATUS_FAILED = "failed"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RecipePreviewJobService:
    """Manages short-lived URL preview jobs in the shared TTL cache."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def create_job(self, source_url: str) -> dict[str, Any]:
        job_id = str(uuid4())
        now = _utc_now_iso()
        job = {
            "job_id": job_id,
            "status": PREVIEW_JOB_STATUS_QUEUED,
            "url": source_url,
            "created_at": now,
            "updated_at": now,
            "message": "Recipe preview import queued.",
        }
        recipe_preview_job_cache.set(job_id, deepcopy(job))
        return deepcopy(job)

    def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        job = recipe_preview_job_cache.get(job_id)
        if job is None:
            return None
        return deepcopy(job)

    def process_job(
        self,
        job_id: str,
        source_url: str,
        processing_service: RecipeProcessingService | None = None,
    ) -> None:
        self._update_job(
            job_id,
            {
                "status": PREVIEW_JOB_STATUS_PROCESSING,
                "message": "Recipe preview import in progress.",
            },
        )

        service = processing_service or RecipeProcessingService()
        recipe, error, diagnostics = service.preview_recipe_from_url(source_url)

        if error or not recipe:
            self._update_job(
                job_id,
                {
                    "status": PREVIEW_JOB_STATUS_FAILED,
                    "success": False,
                    "created": False,
                    "error": error or "Recipe preview failed.",
                    "diagnostics": diagnostics,
                    "message": "Recipe preview import failed.",
                },
                terminal=True,
            )
            return

        self._update_job(
            job_id,
            {
                "status": PREVIEW_JOB_STATUS_COMPLETED,
                "success": True,
                "created": False,
                "recipe_preview": recipe.model_dump(),
                "diagnostics": diagnostics,
                "message": (
                    "Recipe preview generated successfully. No database insertion performed."
                ),
            },
            terminal=True,
        )

    def _update_job(
        self,
        job_id: str,
        changes: dict[str, Any],
        *,
        terminal: bool = False,
    ) -> None:
        with self._lock:
            current_job = recipe_preview_job_cache.get(job_id)
            if current_job is None:
                logger.warning("Recipe preview job missing from cache. job_id=%s", job_id)
                return

            now = _utc_now_iso()
            updated_job = deepcopy(current_job)
            updated_job.update(changes)
            updated_job["updated_at"] = now
            if terminal:
                updated_job["completed_at"] = now

            # Extend TTL when transitioning to PROCESSING so the cache entry
            # cannot expire while the background extraction is still running.
            ttl = (
                RECIPE_PREVIEW_JOB_CACHE_TTL_SECONDS
                if changes.get("status") == PREVIEW_JOB_STATUS_PROCESSING
                else None
            )
            recipe_preview_job_cache.set(job_id, updated_job, ttl_seconds=ttl)
