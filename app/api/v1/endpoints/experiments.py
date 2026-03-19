import json
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.schemas import (
    ExperimentMessageCreateRequest,
    ExperimentThreadCreateRequest,
)
from app.core.config import settings
from app.core.dependencies import get_experiment_service
from app.core.logging import get_logger
from app.services.experiment_service import (
    ExperimentThreadNotFoundError,
    ExperimentValidationError,
)

router = APIRouter(
    prefix=f"{settings.API_V1_STR}/experiments",
    tags=["Experiments"],
)
logger = get_logger(__name__)

EXPERIMENT_BODY = Body()

# Dependency instances to satisfy Ruff B008
experiment_service_dep = Depends(get_experiment_service)


def _to_string_ids(recipe_ids: list[UUID]) -> list[str]:
    return [str(recipe_id) for recipe_id in recipe_ids]


def _to_sse_chunk(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"


@router.post("/threads")
def create_experiment_thread(
    payload: ExperimentThreadCreateRequest = EXPERIMENT_BODY,
    experiment_service=experiment_service_dep,
) -> dict:
    try:
        thread = experiment_service.create_thread(
            mode=payload.mode,
            title=payload.title,
            context_recipe_ids=_to_string_ids(payload.context_recipe_ids),
            is_test=payload.is_test,
        )
        return {"thread": thread, "success": True}
    except ExperimentValidationError as e:
        if e.missing_recipe_ids:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": str(e),
                    "missing_recipe_ids": e.missing_recipe_ids,
                },
            ) from e
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        logger.exception("Error creating experiment thread: %s", e)
        raise HTTPException(
            status_code=500, detail="Error creating experiment thread"
        ) from e


@router.get("/threads")
def list_experiment_threads(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of experiment threads to return.",
    ),
    include_test: bool = Query(
        default=False,
        description="Include threads flagged as test/e2e data.",
    ),
    experiment_service=experiment_service_dep,
) -> dict:
    try:
        threads = experiment_service.list_threads(
            limit=limit,
            include_test=include_test,
        )
        return {"threads": threads, "count": len(threads), "success": True}
    except Exception as e:
        logger.exception("Error listing experiment threads: %s", e)
        raise HTTPException(
            status_code=500, detail="Error listing experiment threads"
        ) from e


@router.get("/threads/{thread_id}")
def get_experiment_thread(
    thread_id: UUID,
    message_limit: int = Query(
        default=120,
        ge=1,
        le=500,
        description="Maximum number of messages to include with the thread payload.",
    ),
    experiment_service=experiment_service_dep,
) -> dict:
    thread_id_str = str(thread_id)
    try:
        thread = experiment_service.get_thread(
            thread_id=thread_id_str,
            message_limit=message_limit,
        )
        return {"thread": thread, "success": True}
    except ExperimentThreadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("Error getting experiment thread %s: %s", thread_id_str, e)
        raise HTTPException(
            status_code=500, detail="Error getting experiment thread"
        ) from e


@router.post("/threads/{thread_id}/messages")
def create_experiment_message(
    thread_id: UUID,
    payload: ExperimentMessageCreateRequest = EXPERIMENT_BODY,
    experiment_service=experiment_service_dep,
) -> dict:
    thread_id_str = str(thread_id)
    context_recipe_ids = (
        _to_string_ids(payload.context_recipe_ids)
        if payload.context_recipe_ids is not None
        else None
    )
    attach_recipe_ids = (
        _to_string_ids(payload.attach_recipe_ids)
        if payload.attach_recipe_ids is not None
        else None
    )
    attach_recipe_names = payload.attach_recipe_names or None
    try:
        response_payload = experiment_service.send_user_message(
            thread_id=thread_id_str,
            content=payload.content,
            context_recipe_ids=context_recipe_ids,
            attach_recipe_ids=attach_recipe_ids,
            attach_recipe_names=attach_recipe_names,
        )
        return {"thread_id": thread_id_str, **response_payload, "success": True}
    except ExperimentThreadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ExperimentValidationError as e:
        if e.missing_recipe_ids:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": str(e),
                    "missing_recipe_ids": e.missing_recipe_ids,
                },
            ) from e
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        logger.exception(
            "Error posting experiment message for thread %s: %s", thread_id_str, e
        )
        raise HTTPException(
            status_code=500, detail="Error creating experiment message"
        ) from e


@router.post("/threads/{thread_id}/messages/stream")
def stream_experiment_message(
    thread_id: UUID,
    payload: ExperimentMessageCreateRequest = EXPERIMENT_BODY,
    experiment_service=experiment_service_dep,
):
    thread_id_str = str(thread_id)
    context_recipe_ids = (
        _to_string_ids(payload.context_recipe_ids)
        if payload.context_recipe_ids is not None
        else None
    )
    attach_recipe_ids = (
        _to_string_ids(payload.attach_recipe_ids)
        if payload.attach_recipe_ids is not None
        else None
    )
    attach_recipe_names = payload.attach_recipe_names or None

    def stream():
        try:
            event_iterator = experiment_service.stream_user_message(
                thread_id=thread_id_str,
                content=payload.content,
                context_recipe_ids=context_recipe_ids,
                attach_recipe_ids=attach_recipe_ids,
                attach_recipe_names=attach_recipe_names,
            )
            for event_payload in event_iterator:
                event_name = str(event_payload.get("event", "message"))
                event_data = event_payload.get("data")
                if not isinstance(event_data, dict):
                    event_data = {"value": event_data}
                yield _to_sse_chunk(event_name, event_data)
        except ExperimentThreadNotFoundError as e:
            yield _to_sse_chunk("error", {"detail": str(e), "status": 404})
        except ExperimentValidationError as e:
            error_payload = {"detail": str(e), "status": 422}
            if e.missing_recipe_ids:
                error_payload["missing_recipe_ids"] = e.missing_recipe_ids
                error_payload["status"] = 404
            yield _to_sse_chunk("error", error_payload)
        except Exception as e:
            logger.exception(
                "Error streaming experiment message for thread %s: %s",
                thread_id_str,
                e,
            )
            yield _to_sse_chunk(
                "error",
                {"detail": "Error creating experiment message stream", "status": 500},
            )

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
