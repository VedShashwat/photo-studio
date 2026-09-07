from typing import cast
from uuid import UUID, uuid4

from app import job_runner as job_runner_module
from app.job_runner import JobRunner
from app.services.db_client import ClaimedJob, WorkerDatabase


class FakeDatabase:
    def __init__(self, job: ClaimedJob) -> None:
        self.job: ClaimedJob = job
        self.failed: tuple[object, str] | None = None

    def claim_next_job(self) -> ClaimedJob:
        return self.job

    def mark_failed(self, job_id: UUID, message: str) -> None:
        self.failed = (job_id, message)


def test_job_runner_marks_gpu_failure_with_durable_context(monkeypatch) -> None:
    job = ClaimedJob(
        id=uuid4(),
        image_id=uuid4(),
        job_type="background_generation",
        scene_preset="luxury_studio",
        prompt="prompt",
        negative_prompt=None,
        variation_count=3,
        base_seed=100,
        settings={},
    )
    database = FakeDatabase(job)
    released = []
    monkeypatch.setattr(job_runner_module, "release_cuda_memory", lambda: released.append(True))

    def fail(_: ClaimedJob) -> None:
        raise RuntimeError("CUDA out of memory while loading weights")

    JobRunner(database, {"background_generation": fail}).run_once()

    assert database.failed is not None
    assert database.failed[0] == job.id
    assert database.failed[1].startswith("GPU/model failure (RuntimeError):")
    assert released == [True]


def test_job_runner_marks_handler_failure() -> None:
    job = ClaimedJob(
        id=uuid4(),
        image_id=uuid4(),
        job_type="background_removal",
        scene_preset=None,
        prompt=None,
        negative_prompt=None,
        variation_count=None,
        base_seed=None,
        settings={},
    )
    database = FakeDatabase(job)

    def fail(_: ClaimedJob) -> None:
        raise RuntimeError("model inference failed")

    returned = JobRunner(cast(WorkerDatabase, database), {"background_removal": fail}).run_once()

    assert returned == job
    assert database.failed == (job.id, "model inference failed")
