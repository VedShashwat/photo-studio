from fastapi.testclient import TestClient

from app.main import create_app


def test_local_frontend_preflight_is_allowed() -> None:
    response = TestClient(create_app()).options(
        "/api/generation-jobs",
        headers={
            "Origin": "http://localhost:3001",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3001"
