import base64
import binascii
import json
from datetime import datetime
from uuid import UUID


class RecipePaginationCursor:
    @staticmethod
    def encode(created_at: datetime, recipe_id: str) -> str:
        if not isinstance(created_at, datetime):
            raise ValueError("Cursor created_at must be a datetime")

        payload = {
            "created_at": created_at.isoformat(),
            "id": recipe_id,
        }
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

    @staticmethod
    def decode(cursor: str) -> tuple[datetime, str]:
        try:
            normalized_cursor = cursor.strip()
            if not normalized_cursor:
                raise ValueError("Cursor cannot be empty")
            padded_cursor = normalized_cursor + "=" * (-len(normalized_cursor) % 4)
            decoded = base64.urlsafe_b64decode(padded_cursor.encode("utf-8")).decode(
                "utf-8"
            )
            payload = json.loads(decoded)
            created_at_value = datetime.fromisoformat(payload["created_at"])
            recipe_id = str(UUID(str(payload["id"])))
            return created_at_value, recipe_id
        except (
            KeyError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
            UnicodeDecodeError,
            binascii.Error,
        ) as exc:
            raise ValueError("Invalid cursor") from exc
