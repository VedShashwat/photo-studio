from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class BackgroundRemovalRequest(BaseModel):
    force: bool = False


class JobResponse(BaseModel):
    job_id: UUID
    image_id: UUID
    job_type: str
    status: str


ScenePreset = Literal[
    "white_amazon",
    "luxury_studio",
    "wooden_table",
    "coffee_shop",
    "office_desk",
    "marble_surface",
    "outdoor_lifestyle",
]


class GenerationSettings(BaseModel):
    steps: int = Field(default=25, ge=20, le=40)
    guidance_scale: float = Field(default=8.0, ge=1, le=20)
    strength: float = Field(default=0.9, ge=0.35, le=0.95)
    controlnet_conditioning_scale: float = Field(default=0.3, ge=0, le=2)
    canvas_size: int = Field(default=512, ge=512, le=2048)


class GenerationJobCreateRequest(BaseModel):
    image_id: UUID
    scene_preset: ScenePreset
    prompt: str | None = Field(default=None, min_length=3, max_length=500)
    negative_prompt: str | None = Field(default=None, min_length=0, max_length=500)
    variation_count: Literal[3, 4]
    seed: int | None = None
    settings: GenerationSettings = Field(default_factory=GenerationSettings)


class GenerationJobCreateResponse(BaseModel):
    job_id: UUID
    status: str
