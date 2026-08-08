from fastapi.testclient import TestClient

from app.main import create_app


def test_health() -> None:
    response = TestClient(create_app()).get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_request_id_is_echoed_for_traceability() -> None:
    request_id = "request-123"
    response = TestClient(create_app()).get("/api/health", headers={"X-Request-ID": request_id})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id
