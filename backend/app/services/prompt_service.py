from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import GenerationJob, PromptHistory
from app.db.repositories.prompts import PromptHistoryRepository
from app.schemas.jobs import GenerationJobCreateRequest
from app.schemas.prompts import PromptHistoryItem, PromptHistoryResponse


class PromptService:
    def __init__(self, session: Session):
        self.session = session
        self.prompts = PromptHistoryRepository(session)

    def record_generation_prompt(self, job: GenerationJob, request: GenerationJobCreateRequest) -> PromptHistory:
        prompt = getattr(job, "prompt", None) or request.prompt or "professional product photography"
        negative_prompt = getattr(job, "negative_prompt", request.negative_prompt)
        settings = getattr(job, "settings", None) or request.settings.model_dump(exclude_none=True)
        history = PromptHistory(
            image_id=request.image_id,
            generation_job_id=job.id,
            scene_preset=request.scene_preset,
            prompt=prompt,
            negative_prompt=negative_prompt,
            settings=settings,
        )
        return self.prompts.add(history)

    def list_history(self, *, page: int = 1, limit: int = 20) -> PromptHistoryResponse:
        if page < 1:
            raise AppError("INVALID_PAGINATION", "Page must be at least 1.", 422)
        if not 1 <= limit <= 50:
            raise AppError("INVALID_PAGINATION", "Limit must be between 1 and 50.", 422)

        prompts, total = self.prompts.list_recent(page, limit)
        return PromptHistoryResponse(
            items=[
                PromptHistoryItem(
                    prompt_id=prompt.id,
                    image_id=prompt.image_id,
                    generation_job_id=prompt.generation_job_id,
                    scene_preset=prompt.scene_preset,
                    prompt=prompt.prompt,
                    negative_prompt=prompt.negative_prompt,
                    settings=prompt.settings or {},
                    created_at=getattr(prompt, "created_at", None),
                )
                for prompt in prompts
            ],
            page=page,
            limit=limit,
            total=total,
            has_next=page * limit < total,
        )
