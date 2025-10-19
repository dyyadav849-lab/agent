from fastapi import status
from fastapi.testclient import TestClient

from app.server import app


def test_health_check() -> None:
    client = TestClient(app)
    response = client.get("/health_check", params={"greeting": "Hello", "name": "John"})
    assert response.status_code == status.HTTP_200_OK
    assert (
        "text/html" in response.headers["Content-Type"]
    ), f"Expected HTML content but got {response.headers['Content-Type']}"


def test_health_check_default() -> None:
    client = TestClient(app)
    response = client.get("/health_check")
    assert response.status_code == status.HTTP_200_OK
    assert (
        "text/html" in response.headers["Content-Type"]
    ), f"Expected HTML content but got {response.headers['Content-Type']}"
