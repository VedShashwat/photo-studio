from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.logging import current_request_id
from app.db.models import GenerationJob
from app.db.repositories.images import ImageRepository
from app.db.repositories.jobs import GenerationJobRepository
from app.db.repositories.outputs import OutputRepository
from app.schemas.history import GenerationHistoryItem, GenerationHistoryResponse, HistoryOutputResponse
from app.schemas.jobs import GenerationJobCreateRequest, GenerationJobCreateResponse, JobResponse
from app.schemas.outputs import GenerationJobStatusResponse, JobProgress, OutputResponse
from app.services.prompt_presets import BASE_NEGATIVE_PROMPT, SCENE_PRESETS
from app.services.prompt_service import PromptService


TERMINAL_STATUSES = {"succeeded", "partially_succeeded", "failed", "cancelled"}
ALL_STATUSES = {"pending", "running", *TERMINAL_STATUSES}
ALLOWED_TRANSITIONS = {
    "pending": {"running", "failed", "cancelled"},
    "running": TERMINAL_STATUSES,
}
VALID_SCENE_PRESETS = frozenset(SCENE_PRESETS)


class JobService:
    def __init__(self, session: Session):
        self.session = session
        self.images = ImageRepository(session)
        self.jobs = GenerationJobRepository(session)
        self.outputs = OutputRepository(session)
        self.prompts = PromptService(session)

    def request_background_removal(self, image_id: UUID, force: bool = False) -> JobResponse:
        """Create or reuse the durable preprocessing job for an image."""
        image = self.images.get(image_id)
        if image is None:
            raise AppError("IMAGE_NOT_FOUND", "Image was not found.", 404)

        previous = self.jobs.latest_for_image(image_id, "background_removal")
        if previous and previous.status in {"pending", "running"} and not force:
            raise AppError(
                "IMAGE_ALREADY_PROCESSING",
                "Background removal is already being processed for this image.",
                409,
            )
        if image.status == "ready" and previous and previous.status == "succeeded" and not force:
            return self._response(previous)

        job = GenerationJob(
            image_id=image_id,
            job_type="background_removal",
            status="pending",
            settings={},
            metrics={"request_id": current_request_id()} if current_request_id() else {},
        )
        image.status = "processing"
        self.jobs.add(job)
        self.session.commit()
        return self._response(job)

    def request_generation(self, request: GenerationJobCreateRequest) -> GenerationJobCreateResponse:
        image = self.images.get(request.image_id)
        if image is None:
            raise AppError("IMAGE_NOT_FOUND", "Image was not found.", 404)
        if image.status != "ready":
            raise AppError("IMAGE_NOT_READY", "Background removal must finish before generation.", 409)
        if request.scene_preset not in VALID_SCENE_PRESETS:
            raise AppError("INVALID_GENERATION_SETTINGS", "Scene preset is not supported.", 422)
        if request.variation_count not in {3, 4}:
            raise AppError("INVALID_GENERATION_SETTINGS", "Variation count must be 3 or 4.", 422)
        if request.prompt is not None and not 3 <= len(request.prompt) <= 500:
            raise AppError("INVALID_GENERATION_SETTINGS", "Prompt must be between 3 and 500 characters.", 422)
        if request.negative_prompt is not None and len(request.negative_prompt) > 500:
            raise AppError("INVALID_GENERATION_SETTINGS", "Negative prompt must be at most 500 characters.", 422)
        self._validate_generation_settings(request)

        prompt = request.prompt or SCENE_PRESETS[request.scene_preset]["prompt"]
        negative_prompt = BASE_NEGATIVE_PROMPT if request.negative_prompt is None else request.negative_prompt

        job = GenerationJob(
            image_id=request.image_id,
            job_type="background_generation",
            status="pending",
            scene_preset=request.scene_preset,
            prompt=prompt,
            negative_prompt=negative_prompt,
            variation_count=request.variation_count,
            base_seed=request.seed,
            settings=request.settings.model_dump(exclude_none=True),
            metrics={"request_id": current_request_id()} if current_request_id() else {},
        )
        self.jobs.add(job)
        self.prompts.record_generation_prompt(job, request)
        self.session.commit()
        return GenerationJobCreateResponse(job_id=job.id, status=job.status)

    @staticmethod
    def _validate_generation_settings(request: GenerationJobCreateRequest) -> None:
        settings = request.settings
        bounds = (
            ("steps", settings.steps, 20, 40),
            ("guidance_scale", settings.guidance_scale, 1, 20),
            ("strength", settings.strength, 0.35, 0.95),
            ("controlnet_conditioning_scale", settings.controlnet_conditioning_scale, 0, 2),
            ("canvas_size", settings.canvas_size, 512, 2048),
        )
        for name, value, minimum, maximum in bounds:
            if value is not None and not minimum <= value <= maximum:
                raise AppError(
                    "INVALID_GENERATION_SETTINGS",
                    f"{name} must be between {minimum} and {maximum}.",
                    422,
                )

    def get_generation_history(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        status: str | None = None,
    ) -> GenerationHistoryResponse:
        if page < 1:
            raise AppError("INVALID_PAGINATION", "Page must be at least 1.", 422)
        if not 1 <= limit <= 50:
            raise AppError("INVALID_PAGINATION", "Limit must be between 1 and 50.", 422)
        if status is not None and status not in ALL_STATUSES:
            raise AppError("INVALID_JOB_STATUS", f"Unsupported job status '{status}'.", 422)

        jobs, total = self.jobs.list_generation_jobs(page, limit, status)
        items = []
        for job in jobs:
            outputs = self.outputs.for_job(job.id)
            image = getattr(job, "image", None)
            if image is None and hasattr(self.session, "scalar"):
                image = self.images.get(job.image_id)
            items.append(
                GenerationHistoryItem(
                    job_id=job.id,
                    image_id=job.image_id,
                    status=job.status,
                    scene_preset=job.scene_preset,
                    prompt=job.prompt,
                    negative_prompt=job.negative_prompt,
                    variation_count=job.variation_count,
                    base_seed=job.base_seed,
                    settings=job.settings or {},
                    created_at=getattr(job, "created_at", None),
                    original_url=f"/api/images/{job.image_id}/original",
                    width=getattr(image, "width", None),
                    height=getattr(image, "height", None),
                    mime_type=getattr(image, "mime_type", None),
                    cutout_url=f"/api/images/{job.image_id}/cutout" if getattr(image, "cutout_path", None) else None,
                    outputs=[
                        HistoryOutputResponse(
                            output_id=output.id,
                            status=output.status,
                            thumbnail_url=f"/api/outputs/{output.id}/image" if output.status == "succeeded" else None,
                            url=f"/api/outputs/{output.id}/image" if output.status == "succeeded" else None,
                            download_url=f"/api/outputs/{output.id}/download" if output.status == "succeeded" else None,
                            seed=output.seed,
                        )
                        for output in outputs
                    ],
                    error_message=job.error_message,
                )
            )

        return GenerationHistoryResponse(
            items=items,
            page=page,
            limit=limit,
            total=total,
            has_next=page * limit < total,
        )

    def get_job(self, job_id: UUID) -> JobResponse:
        job = self.jobs.get(job_id)
        if job is None:
            raise AppError("JOB_NOT_FOUND", "Job was not found.", 404)
        return self._response(job)

    def get_generation_status(self, job_id: UUID) -> GenerationJobStatusResponse:
        job = self.jobs.get(job_id)
        if job is None:
            raise AppError("JOB_NOT_FOUND", "Job was not found.", 404)

        outputs = self.outputs.for_job(job.id)
        total_outputs = job.variation_count or len(outputs)
        return GenerationJobStatusResponse(
            job_id=job.id,
            image_id=job.image_id,
            status=job.status,
            progress=JobProgress(
                completed_outputs=sum(output.status == "succeeded" for output in outputs),
                total_outputs=total_outputs,
            ),
            outputs=[
                OutputResponse(
                    output_id=output.id,
                    status=output.status,
                    url=f"/api/outputs/{output.id}/image",
                    download_url=f"/api/outputs/{output.id}/download",
                    seed=output.seed,
                )
                for output in outputs
            ],
            error_message=job.error_message,
        )

    def transition_job(
        self,
        job_id: UUID,
        status: str,
        *,
        error_message: str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> JobResponse:
        job = self.jobs.get(job_id)
        if job is None:
            raise AppError("JOB_NOT_FOUND", "Job was not found.", 404)
        if status not in ALL_STATUSES:
            raise AppError("INVALID_JOB_STATUS", f"Unsupported job status '{status}'.", 422)
        if status != job.status and status not in ALLOWED_TRANSITIONS.get(job.status, set()):
            raise AppError(
                "INVALID_JOB_TRANSITION",
                f"Job cannot transition from '{job.status}' to '{status}'.",
                409,
            )

        if status != job.status:
            job.status = status
            now = datetime.now(timezone.utc)
            if status == "running":
                job.started_at = now
            if status in TERMINAL_STATUSES:
                job.completed_at = now
        if error_message is not None:
            job.error_message = error_message
        if metrics is not None:
            job.metrics = {**(job.metrics or {}), **metrics}
        self.session.commit()
        return self._response(job)

    @staticmethod
    def _response(job: GenerationJob) -> JobResponse:
        return JobResponse(job_id=job.id, image_id=job.image_id, job_type=job.job_type, status=job.status)
