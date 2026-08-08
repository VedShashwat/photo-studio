from datetime import datetime, timezone
from types import SimpleNamespace
from typing import cast
from uuid import uuid4


from fastapi.testclient import TestClient

from app.api.routes import history as history_route
from app.db.models import GeneratedOutput, GenerationJob, PromptHistory
from app.db.session import get_db
from app.main import create_app
from app.schemas.history import GenerationHistoryResponse
from app.schemas.jobs import GenerationJobCreateRequest, GenerationSettings
from app.schemas.prompts import PromptHistoryResponse
from app.services.job_service import JobService
from app.services.prompt_service import PromptService


class FakeSession:
    pass


def test_generation_history_returns_jobs_and_output_thumbnails(monkeypatch) -> None:
    job_id = uuid4()
    image_id = uuid4()
    succeeded_id = uuid4()
    failed_id = uuid4()
    service = JobService(FakeSession())
    job = cast(
        GenerationJob,
        SimpleNamespace(
            id=job_id,
            image_id=image_id,
            status="partially_succeeded",
            scene_preset="luxury_studio",
            prompt="premium product",
            negative_prompt="distorted label",
            variation_count=3,
            base_seed=100,
            settings={"steps": 30},
            created_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
            error_message="one variation failed",
        ),
    )
    outputs = cast(
        list[GeneratedOutput],
        [
            SimpleNamespace(id=succeeded_id, status="succeeded", seed=100),
            SimpleNamespace(id=failed_id, status="failed", seed=101),
        ],
    )
    monkeypatch.setattr(service.jobs, "list_generation_jobs", lambda page, limit, status=None: ([job], 2))
    monkeypatch.setattr(service.outputs, "for_job", lambda job_id: outputs)

    response = service.get_generation_history(page=2, limit=1, status="partially_succeeded")

    assert response.page == 2
    assert response.limit == 1
    assert response.total == 2
    assert not response.has_next
    assert response.items[0].original_url == f"/api/images/{image_id}/original"
    assert response.items[0].outputs[0].thumbnail_url == f"/api/outputs/{succeeded_id}/image"
    assert response.items[0].outputs[1].thumbnail_url is None


def test_prompt_service_records_generation_prompt_snapshot(monkeypatch) -> None:
    image_id = uuid4()
    job_id = uuid4()
    service = PromptService(FakeSession())
    monkeypatch.setattr(service.prompts, "add", lambda history: history)
    request = GenerationJobCreateRequest(
        image_id=image_id,
        scene_preset="luxury_studio",
        prompt="premium product on stone",
        negative_prompt="distorted label",
        variation_count=3,
        settings=GenerationSettings(steps=30, strength=0.55),
    )

    history = service.record_generation_prompt(SimpleNamespace(id=job_id), request)

    assert history.image_id == image_id
    assert history.generation_job_id == job_id
    assert history.prompt == request.prompt
    assert history.negative_prompt == request.negative_prompt
    assert history.settings == {
        "steps": 30,
        "guidance_scale": 8.0,
        "strength": 0.55,
        "controlnet_conditioning_scale": 0.3,
        "canvas_size": 512,
    }


def test_prompt_history_returns_recent_prompt_snapshots(monkeypatch) -> None:
    prompt_id = uuid4()
    image_id = uuid4()
    job_id = uuid4()
    service = PromptService(FakeSession())
    prompt = cast(
        PromptHistory,
        SimpleNamespace(
            id=prompt_id,
            image_id=image_id,
            generation_job_id=job_id,
            scene_preset="luxury_studio",
            prompt="premium product",
            negative_prompt="distorted label",
            settings={"steps": 30},
            created_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
        ),
    )
    monkeypatch.setattr(service.prompts, "list_recent", lambda page, limit: ([prompt], 1))

    response = service.list_history(page=1, limit=10)

    assert response.total == 1
    assert response.items[0].prompt_id == prompt_id
    assert response.items[0].generation_job_id == job_id
    assert response.items[0].settings == {"steps": 30}


def test_prompt_history_endpoint_returns_recent_prompts(monkeypatch) -> None:
    class FakePromptService:
        def __init__(self, _: object) -> None:
            pass

        def list_history(self, **kwargs: object) -> PromptHistoryResponse:
            assert kwargs == {"page": 2, "limit": 5}
            return PromptHistoryResponse(items=[], page=2, limit=5, total=0, has_next=False)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(history_route, "PromptService", FakePromptService)

    try:
        response = TestClient(app).get("/api/prompts/history?page=2&limit=5")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["page"] == 2


def test_generation_history_endpoint_validates_and_passes_pagination(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeHistoryJobService:
        def __init__(self, _: object) -> None:
            pass

        def get_generation_history(self, **kwargs: object) -> GenerationHistoryResponse:
            captured.update(kwargs)
            return GenerationHistoryResponse(items=[], page=3, limit=10, total=0, has_next=False)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(history_route, "JobService", FakeHistoryJobService)

    try:
        response = TestClient(app).get("/api/generation-jobs?page=3&limit=10&status=failed")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured == {"page": 3, "limit": 10, "status": "failed"}


def test_generation_history_endpoint_rejects_invalid_limit() -> None:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: object()

    try:
        response = TestClient(app).get("/api/generation-jobs?limit=51")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
