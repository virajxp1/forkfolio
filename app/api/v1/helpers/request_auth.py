from uuid import UUID

from fastapi import HTTPException, Request


def viewer_user_id_from_request(request: Request) -> str | None:
    raw_value = request.headers.get("x-viewer-user-id", "").strip()
    if not raw_value:
        return None
    try:
        return str(UUID(raw_value))
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="Invalid X-Viewer-User-Id header"
        ) from exc
