#!/usr/bin/env python3
"""Container healthcheck that supports API auth token headers."""

import os
import sys
import urllib.request

from app.core.config import settings


def _default_healthcheck_url() -> str:
    api_base_path = settings.API_V1_STR.strip() or "/api/v1"
    if not api_base_path.startswith("/"):
        api_base_path = f"/{api_base_path}"
    api_base_path = api_base_path.rstrip("/")
    return f"http://localhost:8000{api_base_path}/health"


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
