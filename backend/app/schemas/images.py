from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    image_id: UUID
    status: str
    original_url: str
    width: int
    height: int
    mime_type: str


class ImageMetadataResponse(BaseModel):
    image_id: UUID
    status: str
    original_url: str
    mask_url: str | None = None
    cutout_url: str | None = None
    width: int
    height: int
    mime_type: str
    metadata: dict[str, Any]
