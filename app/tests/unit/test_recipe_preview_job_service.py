import time

from app.api.schemas import Recipe
from app.core.cache import recipe_preview_job_cache
from app.services.recipe_preview_job_service import (
    PREVIEW_JOB_STATUS_COMPLETED,
    PREVIEW_JOB_STATUS_FAILED,
    PREVIEW_JOB_STATUS_PROCESSING,
    PREVIEW_JOB_STATUS_QUEUED,
    RecipePreviewJobService,
)


class FakeProcessingService:
    def __init__(
        self,
        recipe: Recipe | None = None,
        error: str | None = None,
        diagnostics: dict[str, int] | None = None,
    ) -> None:
        self.recipe = recipe
        self.error = error
        self.diagnostics = diagnostics or {}

    def preview_recipe_from_url(
        self, source_url: str
    ) -> tuple[Recipe | None, str | None, dict[str, int]]:
        del source_url
        return self.recipe, self.error, self.diagnostics


class SlowProcessingService:
    def preview_recipe_from_url(
        self, source_url: str
    ) -> tuple[Recipe | None, str | None, dict[str, int]]:
        del source_url
        time.sleep(0.2)
        return None, "late result", {}


class CrashingProcessingService:
    def preview_recipe_from_url(
        self, source_url: str
    ) -> tuple[Recipe | None, str | None, dict[str, int]]:
        del source_url
        raise RuntimeError("preview worker exploded")


def setup_function() -> None:
    recipe_preview_job_cache.clear()


def test_recipe_preview_job_service_marks_completed_jobs() -> None:
    service = RecipePreviewJobService()
    job = service.create_job("https://example.com/lemon-pasta")

    assert job["status"] == PREVIEW_JOB_STATUS_QUEUED

    service.process_job(
        job["job_id"],
        job["url"],
        processing_service=FakeProcessingService(
            recipe=Recipe(
                title="Lemon Pasta",
                ingredients=["200g pasta", "1 lemon"],
                instructions=["Boil pasta", "Toss with lemon"],
                servings="2",
                total_time="20 minutes",
            ),
            diagnostics={"scrapegraphai_success": 1},
        ),
    )

    updated_job = service.get_job(job["job_id"])

    assert updated_job is not None
    assert updated_job["status"] == PREVIEW_JOB_STATUS_COMPLETED
    assert updated_job["success"] is True
    assert updated_job["created"] is False
    assert updated_job["recipe_preview"]["title"] == "Lemon Pasta"
    assert updated_job["diagnostics"]["scrapegraphai_success"] == 1
    assert "completed_at" in updated_job


def test_recipe_preview_job_service_marks_failed_jobs() -> None:
    service = RecipePreviewJobService()
    job = service.create_job("https://example.com/missing")

    service.process_job(
        job["job_id"],
        job["url"],
        processing_service=FakeProcessingService(
            recipe=None,
            error="Recipe extraction failed",
            diagnostics={"scrapegraphai_attempted": 1},
        ),
    )

    updated_job = service.get_job(job["job_id"])

    assert updated_job is not None
    assert updated_job["status"] == PREVIEW_JOB_STATUS_FAILED
    assert updated_job["success"] is False
    assert updated_job["error"] == "Recipe extraction failed"
    assert updated_job["diagnostics"]["scrapegraphai_attempted"] == 1
    assert "completed_at" in updated_job


def test_recipe_preview_job_service_marks_processing_before_terminal_status() -> None:
    service = RecipePreviewJobService()
    job = service.create_job("https://example.com/pending")

    service._update_job(  # noqa: SLF001 - intentional unit coverage of status transition
        job["job_id"],
        {
            "status": PREVIEW_JOB_STATUS_PROCESSING,
            "message": "Recipe preview import in progress.",
        },
    )

    updated_job = service.get_job(job["job_id"])

    assert updated_job is not None
    assert updated_job["status"] == PREVIEW_JOB_STATUS_PROCESSING


def test_recipe_preview_job_service_marks_job_failed_when_processing_exceeds_timeout() -> None:
    service = RecipePreviewJobService(timeout_seconds=0.01)
    job = service.create_job("https://example.com/slow")

    started_at = time.monotonic()
    service.process_job(
        job["job_id"],
        job["url"],
        processing_service=SlowProcessingService(),
    )
    elapsed = time.monotonic() - started_at

    updated_job = service.get_job(job["job_id"])

    assert elapsed >= 0.2
    assert updated_job is not None
    assert updated_job["status"] == PREVIEW_JOB_STATUS_FAILED
    assert "timed out" in updated_job["error"]


def test_recipe_preview_job_service_marks_unexpected_worker_exceptions_failed() -> None:
    service = RecipePreviewJobService()
    job = service.create_job("https://example.com/crash")

    service.process_job(
        job["job_id"],
        job["url"],
        processing_service=CrashingProcessingService(),
    )

    updated_job = service.get_job(job["job_id"])

    assert updated_job is not None
    assert updated_job["status"] == PREVIEW_JOB_STATUS_FAILED
    assert updated_job["success"] is False
    assert "failed unexpectedly" in updated_job["error"]
    assert "completed_at" in updated_job
