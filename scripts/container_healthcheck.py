#!/usr/bin/env python3
"""Container healthcheck that supports API auth token headers."""

import os
import sys
import urllib.request

from app.core.config import settings


def _default_healthcheck_url() -> str:
    port = os.getenv("PORT", "8000").strip() or "8000"
    return f"http://localhost:{port}{settings.API_BASE_PATH}/health"


def main() -> int:
    url = os.getenv("HEALTHCHECK_URL", _default_healthcheck_url())
    token = settings.API_AUTH_TOKEN.strip()

    headers: dict[str, str] = {}
    if token:
        headers["X-API-Token"] = token

    request = urllib.request.Request(url=url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return 0 if 200 <= response.status < 300 else 1
    except Exception as exc:
        print(f"Healthcheck failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
