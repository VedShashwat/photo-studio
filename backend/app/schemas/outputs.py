from uuid import UUID

from pydantic import BaseModel


class OutputResponse(BaseModel):
    output_id: UUID
    status: str
    url: str
    download_url: str
    seed: int | None = None


class JobProgress(BaseModel):
    completed_outputs: int
    total_outputs: int


class GenerationJobStatusResponse(BaseModel):
    job_id: UUID
    image_id: UUID
    status: str
    progress: JobProgress
    outputs: list[OutputResponse]
    error_message: str | None = None
