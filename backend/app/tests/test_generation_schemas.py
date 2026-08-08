from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.jobs import GenerationJobCreateRequest, GenerationSettings
from app.schemas.outputs import GenerationJobStatusResponse, JobProgress


def test_generation_request_schema_documents_generation_settings() -> None:
    request = GenerationJobCreateRequest(
        image_id=uuid4(),
        scene_preset="luxury_studio",
        prompt="premium skincare bottle on a dark stone surface",
        negative_prompt="distorted label",
        variation_count=4,
        seed=12345,
        settings=GenerationSettings(steps=30, strength=0.55, canvas_size=1024),
    )

    assert request.settings.steps == 30
    assert request.settings.strength == 0.55
    assert request.settings.canvas_size == 1024


def test_generation_status_schema_supports_outputs_and_progress() -> None:
    status = GenerationJobStatusResponse(
        job_id=uuid4(),
        image_id=uuid4(),
        status="pending",
        progress=JobProgress(completed_outputs=0, total_outputs=4),
        outputs=[],
    )

    assert status.progress.total_outputs == 4
    assert status.outputs == []


def test_generation_schema_rejects_invalid_prompt_and_settings() -> None:
    with pytest.raises(ValidationError):
        GenerationJobCreateRequest(
            image_id=uuid4(),
            scene_preset="luxury_studio",
            prompt="no",
            variation_count=4,
        )
    with pytest.raises(ValidationError):
        GenerationSettings(steps=50)
