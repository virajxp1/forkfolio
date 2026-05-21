from __future__ import annotations

import multiprocessing
import os
import queue
import threading
from copy import deepcopy
from datetime import datetime, timezone
from multiprocessing.context import BaseContext, Process
from typing import Any, Optional, Protocol
from uuid import uuid4

from app.core.cache import RECIPE_PREVIEW_JOB_CACHE_TTL_SECONDS
from app.core.job_store import recipe_preview_job_store
from app.core.logging import get_logger
from app.services.recipe_processing_service import RecipeProcessingService

logger = get_logger(__name__)

PREVIEW_JOB_STATUS_QUEUED = "queued"
PREVIEW_JOB_STATUS_PROCESSING = "processing"
PREVIEW_JOB_STATUS_COMPLETED = "completed"
PREVIEW_JOB_STATUS_FAILED = "failed"

# Backend timeout for a single extraction job (seconds). Should be comfortably
# less than the frontend's 5-minute polling window so clients can observe FAILED.
_DEFAULT_JOB_TIMEOUT_SECONDS = float(
    os.getenv("RECIPE_PREVIEW_JOB_TIMEOUT_SECONDS", "240")
)
_DEFAULT_WORKER_TERMINATE_GRACE_SECONDS = float(
    os.getenv("RECIPE_PREVIEW_JOB_TERMINATE_GRACE_SECONDS", "2")
)
_DEFAULT_WORKER_START_METHOD = os.getenv(
    "RECIPE_PREVIEW_JOB_START_METHOD", "spawn"
).strip()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PreviewRecipeProcessor(Protocol):
    def preview_recipe_from_url(
        self, source_url: str
    ) -> tuple[Any | None, str | None, dict[str, Any]]:
        """Return recipe preview data, an error, and diagnostic counters."""


def _coerce_diagnostics(diagnostics: Any) -> dict[str, Any]:
    return diagnostics if isinstance(diagnostics, dict) else {}


def _run_preview_worker(
    source_url: str,
    result_queue: Any,
    processing_service: PreviewRecipeProcessor | None,
) -> None:
    """Run preview extraction in an isolated child process."""
    service = processing_service or RecipeProcessingService()
    try:
        recipe, error, diagnostics = service.preview_recipe_from_url(source_url)
        result_queue.put(
            {
                "recipe_preview": (
                    recipe.model_dump() if hasattr(recipe, "model_dump") else recipe
                ),
                "error": error,
                "diagnostics": _coerce_diagnostics(diagnostics),
                "worker_error": None,
            }
        )
    except Exception as exc:
        logger.exception(
            "Recipe preview worker crashed unexpectedly. url=%s",
            source_url,
        )
        result_queue.put(
            {
                "recipe_preview": None,
                "error": None,
                "diagnostics": {},
                "worker_error": str(exc),
            }
        )


def _get_worker_context() -> BaseContext:
    if _DEFAULT_WORKER_START_METHOD:
        return multiprocessing.get_context(_DEFAULT_WORKER_START_METHOD)
    return multiprocessing.get_context()


class RecipePreviewJobService:
    """Manages short-lived URL preview jobs via the configured job store."""

    # Class-level lock so all per-request instances share the same guard for
    # read-modify-write updates against the same underlying store.
    _update_lock = threading.Lock()

    def __init__(
        self,
        timeout_seconds: float | None = None,
        processing_service: PreviewRecipeProcessor | None = None,
        worker_context: BaseContext | None = None,
        worker_terminate_grace_seconds: float = _DEFAULT_WORKER_TERMINATE_GRACE_SECONDS,
    ) -> None:
        self._timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else _DEFAULT_JOB_TIMEOUT_SECONDS
        )
        self._processing_service = processing_service
        self._worker_context = worker_context or _get_worker_context()
        self._worker_terminate_grace_seconds = worker_terminate_grace_seconds

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
        recipe_preview_job_store.set(job_id, deepcopy(job))
        return deepcopy(job)

    def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        return recipe_preview_job_store.get(job_id)

    def process_job(
        self,
        job_id: str,
        source_url: str,
        processing_service: PreviewRecipeProcessor | None = None,
    ) -> None:
        self._update_job(
            job_id,
            {
                "status": PREVIEW_JOB_STATUS_PROCESSING,
                "message": "Recipe preview import in progress.",
            },
        )

        result = self._run_preview_with_timeout(
            source_url,
            processing_service or self._processing_service,
        )
        if result is None:
            logger.warning(
                "Recipe preview job timed out after %.0fs. job_id=%s url=%s",
                self._timeout_seconds,
                job_id,
                source_url,
            )
            self._mark_failed(
                job_id,
                error=f"Recipe preview timed out after {int(self._timeout_seconds)}s.",
                diagnostics={},
                message="Recipe preview import timed out.",
            )
            return

        worker_error = result.get("worker_error")
        if worker_error:
            logger.error(
                "Recipe preview job crashed unexpectedly. job_id=%s url=%s",
                job_id,
                source_url,
            )
            self._mark_failed(
                job_id,
                error=f"Recipe preview failed unexpectedly: {worker_error}",
                diagnostics=_coerce_diagnostics(result.get("diagnostics")),
                message="Recipe preview import failed unexpectedly.",
            )
            return

        recipe_preview = result.get("recipe_preview")
        error = result.get("error")
        diagnostics = _coerce_diagnostics(result.get("diagnostics"))

        if error or not recipe_preview:
            self._mark_failed(
                job_id,
                error=error or "Recipe preview failed.",
                diagnostics=diagnostics,
                message="Recipe preview import failed.",
            )
            return

        self._update_job(
            job_id,
            {
                "status": PREVIEW_JOB_STATUS_COMPLETED,
                "success": True,
                "created": False,
                "recipe_preview": recipe_preview,
                "diagnostics": diagnostics,
                "message": (
                    "Recipe preview generated successfully. No database insertion performed."
                ),
            },
            terminal=True,
        )

    def _run_preview_with_timeout(
        self,
        source_url: str,
        processing_service: PreviewRecipeProcessor | None,
    ) -> dict[str, Any] | None:
        result_queue = self._worker_context.Queue(maxsize=1)
        process = self._worker_context.Process(
            target=_run_preview_worker,
            args=(source_url, result_queue, processing_service),
            name="recipe-preview-worker",
        )
        try:
            process.start()
            process.join(timeout=self._timeout_seconds)

            if process.is_alive():
                self._terminate_worker(process)
                return None

            try:
                result = result_queue.get(timeout=0.1)
            except queue.Empty:
                return {
                    "recipe_preview": None,
                    "error": None,
                    "diagnostics": {},
                    "worker_error": (
                        f"worker exited without returning a result "
                        f"(exitcode={process.exitcode})"
                    ),
                }

            return (
                result
                if isinstance(result, dict)
                else {
                    "recipe_preview": None,
                    "error": None,
                    "diagnostics": {},
                    "worker_error": "worker returned an invalid result",
                }
            )
        except Exception as exc:
            logger.exception(
                "Recipe preview worker failed to start or complete. url=%s",
                source_url,
            )
            return {
                "recipe_preview": None,
                "error": None,
                "diagnostics": {},
                "worker_error": str(exc),
            }
        finally:
            result_queue.close()
            result_queue.join_thread()

    def _terminate_worker(self, process: Process) -> None:
        process.terminate()
        process.join(timeout=self._worker_terminate_grace_seconds)
        if process.is_alive():
            process.kill()
            process.join()

    def _mark_failed(
        self,
        job_id: str,
        *,
        error: str,
        diagnostics: dict[str, Any],
        message: str,
    ) -> None:
        self._update_job(
            job_id,
            {
                "status": PREVIEW_JOB_STATUS_FAILED,
                "success": False,
                "created": False,
                "error": error,
                "diagnostics": diagnostics,
                "message": message,
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
        with self._update_lock:
            current_job = recipe_preview_job_store.get(job_id)
            if current_job is None:
                logger.warning(
                    "Recipe preview job missing from store. job_id=%s", job_id
                )
                return

            now = _utc_now_iso()
            updated_job = deepcopy(current_job)
            updated_job.update(changes)
            updated_job["updated_at"] = now
            if terminal:
                updated_job["completed_at"] = now

            # Extend TTL when transitioning to PROCESSING so the store entry
            # cannot expire while the background extraction is still running.
            ttl = (
                RECIPE_PREVIEW_JOB_CACHE_TTL_SECONDS
                if changes.get("status") == PREVIEW_JOB_STATUS_PROCESSING
                else None
            )
            recipe_preview_job_store.set(job_id, updated_job, ttl_seconds=ttl)
