"""
E2E smoke checks for health endpoints.
"""

from app.tests.clients.api_client import APIClient
from app.tests.utils.constants import HTTP_OK


def test_root_endpoint(api_client: APIClient) -> None:
    response = api_client.health.get_root()
    assert response["status_code"] == HTTP_OK
    assert response["data"] == {"message": "Welcome to ForkFolio API"}


def test_health_endpoint_contract(api_client: APIClient) -> None:
    response = api_client.health.health_check()
    assert response["status_code"] == HTTP_OK

    payload = response["data"]
    assert payload["status"] in {"healthy", "unhealthy"}
    assert isinstance(payload.get("database"), dict)
    assert isinstance(payload.get("timestamp"), str)
