from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.services.job_service import JobService


class FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0

    def commit(self) -> None:
        self.commit_count += 1


def test_request_background_removal_creates_pending_job() -> None:
    image_id = uuid4()
    job_id = uuid4()
    session = FakeSession()
    service = JobService(session)
    image = SimpleNamespace(id=image_id, status="uploaded")

    service.images.get = lambda _: image
    service.jobs.latest_for_image = lambda *_: None

    def add(job) -> None:
        job.id = job_id

    service.jobs.add = add

    response = service.request_background_removal(image_id)

    assert response.job_id == job_id
    assert response.image_id == image_id
    assert response.status == "pending"
    assert image.status == "processing"
    assert session.commit_count == 1


def test_request_background_removal_rejects_duplicate_processing() -> None:
    image_id = uuid4()
    session = FakeSession()
    service = JobService(session)
    service.images.get = lambda _: SimpleNamespace(id=image_id, status="processing")
    service.jobs.latest_for_image = lambda *_: SimpleNamespace(status="running")

    with pytest.raises(AppError) as error:
        service.request_background_removal(image_id)

    assert error.value.code == "IMAGE_ALREADY_PROCESSING"
    assert error.value.status_code == 409
    assert session.commit_count == 0


def test_get_job_returns_not_found_error() -> None:
    service = JobService(FakeSession())
    service.jobs.get = lambda _: None

    with pytest.raises(AppError) as error:
        service.get_job(uuid4())

    assert error.value.code == "JOB_NOT_FOUND"
    assert error.value.status_code == 404


def test_transition_job_records_running_and_terminal_timestamps() -> None:
    job = SimpleNamespace(
        id=uuid4(),
        image_id=uuid4(),
        job_type="background_removal",
        status="pending",
        started_at=None,
        completed_at=None,
        error_message=None,
        metrics={},
    )
    session = FakeSession()
    service = JobService(session)
    service.jobs.get = lambda _: job

    running = service.transition_job(job.id, "running")
    succeeded = service.transition_job(job.id, "succeeded", metrics={"duration_ms": 12})

    assert running.status == "running"
    assert succeeded.status == "succeeded"
    assert job.started_at is not None
    assert job.completed_at is not None
    assert job.metrics == {"duration_ms": 12}
    assert session.commit_count == 2


def test_transition_job_rejects_backward_transition() -> None:
    job = SimpleNamespace(
        id=uuid4(),
        image_id=uuid4(),
        job_type="background_removal",
        status="running",
        started_at=None,
        completed_at=None,
        error_message=None,
        metrics={},
    )
    service = JobService(FakeSession())
    service.jobs.get = lambda _: job

    with pytest.raises(AppError) as error:
        service.transition_job(job.id, "pending")

    assert error.value.code == "INVALID_JOB_TRANSITION"
    assert error.value.status_code == 409
