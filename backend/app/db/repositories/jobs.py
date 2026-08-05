import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import GenerationJob


class GenerationJobRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, job_id: uuid.UUID) -> GenerationJob | None:
        return self.session.scalar(select(GenerationJob).where(GenerationJob.id == job_id))

    def add(self, job: GenerationJob) -> GenerationJob:
        self.session.add(job)
        self.session.flush()
        return job

    def latest_for_image(self, image_id: uuid.UUID, job_type: str) -> GenerationJob | None:
        return self.session.scalar(
            select(GenerationJob)
            .where(GenerationJob.image_id == image_id, GenerationJob.job_type == job_type)
            .order_by(GenerationJob.created_at.desc())
            .limit(1)
        )

    def list_generation_jobs(self, page: int, limit: int, status: str | None = None) -> tuple[list[GenerationJob], int]:
        filters = [GenerationJob.job_type == "background_generation"]
        if status is not None:
            filters.append(GenerationJob.status == status)

        query = select(GenerationJob).where(*filters)
        total = self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        jobs = list(
            self.session.scalars(
                query.order_by(GenerationJob.created_at.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
        )
        return jobs, total
