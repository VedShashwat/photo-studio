from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.jobs import GenerationJobCreateRequest, GenerationJobCreateResponse
from app.schemas.outputs import GenerationJobStatusResponse
from app.services.job_service import JobService


router = APIRouter(prefix="/generation-jobs", tags=["generation-jobs"])


@router.post("", response_model=GenerationJobCreateResponse, status_code=202)
def create_generation_job(
    request: GenerationJobCreateRequest,
    db: Session = Depends(get_db),
) -> GenerationJobCreateResponse:
    return JobService(db).request_generation(request)


@router.get("/{job_id}", response_model=GenerationJobStatusResponse)
def get_generation_job(job_id: UUID, db: Session = Depends(get_db)) -> GenerationJobStatusResponse:
    return JobService(db).get_generation_status(job_id)
