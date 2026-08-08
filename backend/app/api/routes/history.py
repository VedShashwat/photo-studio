from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.history import GenerationHistoryResponse
from app.schemas.prompts import PromptHistoryResponse
from app.services.job_service import JobService
from app.services.prompt_service import PromptService


router = APIRouter(prefix="/generation-jobs", tags=["history"])
prompt_router = APIRouter(prefix="/prompts", tags=["history"])


@router.get("", response_model=GenerationHistoryResponse)
def list_generation_history(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> GenerationHistoryResponse:
    return JobService(db).get_generation_history(page=page, limit=limit, status=status)


@prompt_router.get("/history", response_model=PromptHistoryResponse)
def list_prompt_history(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> PromptHistoryResponse:
    return PromptService(db).list_history(page=page, limit=limit)
