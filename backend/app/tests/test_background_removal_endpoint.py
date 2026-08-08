from typing import cast
from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.routes import images as images_route
from app.db.session import get_db
from app.main import create_app
from app.schemas.jobs import JobResponse


class FakeJobService:
    last_force: bool | None = None

    def __init__(self, _: object) -> None:
        pass

    def request_background_removal(self, image_id: UUID, force: bool = False) -> JobResponse:
        self.last_force = force
        FakeJobService.last_force = force
        return JobResponse(
            job_id=uuid4(),
            image_id=image_id,
            job_type="background_removal",
            status="pending",
        )


def test_remove_background_creates_pending_job_and_forwards_force() -> None:
    image_id = uuid4()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: object()

    with patch.object(images_route, "JobService", FakeJobService):
        response = TestClient(app).post(
            f"/api/images/{image_id}/remove-background",
            json={"force": True},
        )
    app.dependency_overrides.clear()

    assert response.status_code == 202
    payload = cast(dict[str, str], response.json())
    assert payload["image_id"] == str(image_id)
    assert payload["job_type"] == "background_removal"
    assert payload["status"] == "pending"
    assert FakeJobService.last_force is True
