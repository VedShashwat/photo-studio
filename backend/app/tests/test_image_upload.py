from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.db.session import get_db
from app.main import create_app


class FakeSession:
    def add(self, _: object) -> None:
        pass

    def flush(self) -> None:
        pass

    def commit(self) -> None:
        pass


def test_upload_image_persists_normalized_artifact(tmp_path) -> None:
    buffer = BytesIO()
    Image.new("RGB", (640, 512), "white").save(buffer, format="JPEG")
    settings = get_settings()
    original_root = settings.storage_root
    settings.storage_root = str(tmp_path)
    app = create_app()
    app.dependency_overrides[get_db] = lambda: FakeSession()
    try:
        response = TestClient(app).post(
            "/api/images",
            files={"file": ("product.jpg", buffer.getvalue(), "image/jpeg")},
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["status"] == "uploaded"
        assert payload["mime_type"] == "image/jpeg"
        assert list(tmp_path.rglob("artifact.jpg"))
    finally:
        settings.storage_root = original_root
