from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.routes import downloads as downloads_route
from app.db.session import get_db
from app.main import create_app


class FakeOutputRepository:
    output: object | None = None

    def __init__(self, _: object) -> None:
        pass

    def get(self, _: object) -> object | None:
        return self.output


class FakeStorageService:
    output_path: Path = Path()

    def __init__(self, _: str) -> None:
        pass

    def open_path(self, _: str) -> Path:
        return self.output_path


def test_output_routes_stream_and_download_succeeded_output(tmp_path, monkeypatch) -> None:
    output_id = uuid4()
    artifact = tmp_path / "artifact.png"
    artifact.write_bytes(b"png bytes")
    FakeOutputRepository.output = SimpleNamespace(id=output_id, status="succeeded", output_path="outputs/artifact.png")
    FakeStorageService.output_path = artifact
    monkeypatch.setattr(downloads_route, "OutputRepository", FakeOutputRepository)
    monkeypatch.setattr(downloads_route, "StorageService", FakeStorageService)
    app = create_app()
    app.dependency_overrides[get_db] = lambda: object()

    try:
        client = TestClient(app)
        image_response = client.get(f"/api/outputs/{output_id}/image")
        download_response = client.get(f"/api/outputs/{output_id}/download")
    finally:
        app.dependency_overrides.clear()

    assert image_response.status_code == 200
    assert image_response.content == b"png bytes"
    assert download_response.status_code == 200
    assert "attachment" in download_response.headers["content-disposition"]


def test_output_route_rejects_unfinished_output(monkeypatch) -> None:
    output_id = uuid4()
    FakeOutputRepository.output = SimpleNamespace(id=output_id, status="pending", output_path="outputs/artifact.png")
    monkeypatch.setattr(downloads_route, "OutputRepository", FakeOutputRepository)
    app = create_app()
    app.dependency_overrides[get_db] = lambda: object()

    try:
        response = TestClient(app).get(f"/api/outputs/{output_id}/image")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "OUTPUT_NOT_READY"
