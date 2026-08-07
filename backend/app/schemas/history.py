from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class HistoryOutputResponse(BaseModel):
    output_id: UUID
    status: str
    thumbnail_url: str | None
    url: str | None
    download_url: str | None
    seed: int | None = None


class GenerationHistoryItem(BaseModel):
    job_id: UUID
    image_id: UUID
    status: str
    scene_preset: str | None
    prompt: str | None
    negative_prompt: str | None
    variation_count: int | None
    base_seed: int | None
    settings: dict[str, Any]
    created_at: datetime | None
    original_url: str
    width: int | None = None
    height: int | None = None
    mime_type: str | None = None
    cutout_url: str | None = None
    outputs: list[HistoryOutputResponse]
    error_message: str | None = None


class GenerationHistoryResponse(BaseModel):
    items: list[GenerationHistoryItem]
    page: int
    limit: int
    total: int
    has_next: bool
