from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class PromptHistoryItem(BaseModel):
    prompt_id: UUID
    image_id: UUID
    generation_job_id: UUID | None
    scene_preset: str | None
    prompt: str
    negative_prompt: str | None
    settings: dict[str, Any]
    created_at: datetime | None


class PromptHistoryResponse(BaseModel):
    items: list[PromptHistoryItem]
    page: int
    limit: int
    total: int
    has_next: bool
