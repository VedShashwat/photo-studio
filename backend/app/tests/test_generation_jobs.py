from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes import generation_jobs as generation_jobs_route
from app.core.errors import AppError
from app.db.session import get_db
from app.main import create_app
from app.schemas.jobs import GenerationJobCreateRequest, GenerationJobCreateResponse, GenerationSettings
from app.schemas.outputs import GenerationJobStatusResponse
from app.services.job_service import JobService


class FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0

    def add(self, _: object) -> None:
        pass

    def flush(self) -> None:
        pass

    def commit(self) -> None:
        self.commit_count += 1


def test_request_generation_creates_pending_job_for_ready_image() -> None:
    image_id = uuid4()
    job_id = uuid4()
    session = FakeSession()
    service = JobService(session)
    service.images.get = lambda _: SimpleNamespace(id=image_id, status="ready")

    def add(job) -> None:
        job.id = job_id

    service.jobs.add = add
    recorded: list[tuple[object, GenerationJobCreateRequest]] = []
    service.prompts.record_generation_prompt = lambda job, request: recorded.append((job, request))
    request = GenerationJobCreateRequest(
        image_id=image_id,
        scene_preset="luxury_studio",
        prompt="premium bottle on a dark stone surface",
        variation_count=4,
        settings=GenerationSettings(steps=30, strength=0.55),
    )

    response = service.request_generation(request)

    assert response == GenerationJobCreateResponse(job_id=job_id, status="pending")
    assert recorded[0][1] == request
    assert session.commit_count == 1


def test_request_generation_resolves_preset_prompt_and_default_negative_prompt() -> None:
    image_id = uuid4()
    service = JobService(FakeSession())
    service.images.get = lambda _: SimpleNamespace(id=image_id, status="ready")
    captured: list[object] = []

    def capture_job(job) -> None:
        job.id = uuid4()
        captured.append(job)

    service.jobs.add = capture_job
    service.prompts.record_generation_prompt = lambda *_: None

    service.request_generation(
        GenerationJobCreateRequest(
            image_id=image_id,
            scene_preset="coffee_shop",
            variation_count=3,
        )
    )

    job = captured[0]
    assert "coffee shop interior" in job.prompt
    assert "extra object" not in job.negative_prompt
    assert "extra product" in job.negative_prompt


def test_get_generation_status_reports_progress_and_output_urls() -> None:
    job_id = uuid4()
    image_id = uuid4()
    output_id = uuid4()
    service = JobService(FakeSession())
    service.jobs.get = lambda _: SimpleNamespace(
        id=job_id,
        image_id=image_id,
        status="running",
        variation_count=3,
        error_message=None,
    )
    service.outputs.for_job = lambda _: [SimpleNamespace(id=output_id, status="succeeded", seed=123)]

    response = service.get_generation_status(job_id)

    assert response.status == "running"
    assert response.progress.completed_outputs == 1
    assert response.progress.total_outputs == 3
    assert response.outputs[0].url == f"/api/outputs/{output_id}/image"
    assert response.outputs[0].download_url == f"/api/outputs/{output_id}/download"


def test_generation_job_endpoint_rejects_invalid_request_before_service(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: object()

    try:
        response = TestClient(app).post(
            "/api/generation-jobs",
            json={
                "image_id": str(uuid4()),
                "scene_preset": "luxury_studio",
                "prompt": "premium bottle on a dark stone surface",
                "variation_count": 2,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_request_generation_rejects_image_that_is_not_ready() -> None:
    image_id = uuid4()
    service = JobService(FakeSession())
    service.images.get = lambda _: SimpleNamespace(id=image_id, status="processing")
    request = GenerationJobCreateRequest(
        image_id=image_id,
        scene_preset="luxury_studio",
        variation_count=3,
    )

    with pytest.raises(AppError) as error:
        service.request_generation(request)

    assert error.value.code == "IMAGE_NOT_READY"
    assert error.value.status_code == 409


class FakeGenerationJobService:
    def __init__(self, _: object) -> None:
        pass

    def request_generation(self, _: GenerationJobCreateRequest) -> GenerationJobCreateResponse:
        return GenerationJobCreateResponse(job_id=uuid4(), status="pending")

    def get_generation_status(self, job_id) -> GenerationJobStatusResponse:
        return GenerationJobStatusResponse(
            job_id=job_id,
            image_id=uuid4(),
            status="running",
            progress={"completed_outputs": 0, "total_outputs": 3},
            outputs=[],
        )


def test_generation_job_endpoint_returns_pending_response(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(generation_jobs_route, "JobService", FakeGenerationJobService)

    try:
        response = TestClient(app).post(
            "/api/generation-jobs",
            json={
                "image_id": str(uuid4()),
                "scene_preset": "luxury_studio",
                "prompt": "premium bottle on a dark stone surface",
                "variation_count": 4,
                "settings": {"steps": 30, "strength": 0.55},
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["status"] == "pending"


def test_generation_job_status_endpoint_returns_progress(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(generation_jobs_route, "JobService", FakeGenerationJobService)
    job_id = uuid4()

    try:
        response = TestClient(app).get(f"/api/generation-jobs/{job_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["progress"]["total_outputs"] == 3
