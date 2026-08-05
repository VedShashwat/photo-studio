import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import GeneratedOutput


class OutputRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, output_id: uuid.UUID) -> GeneratedOutput | None:
        return self.session.scalar(select(GeneratedOutput).where(GeneratedOutput.id == output_id))

    def for_job(self, job_id: uuid.UUID) -> list[GeneratedOutput]:
        return list(
            self.session.scalars(
                select(GeneratedOutput)
                .where(GeneratedOutput.generation_job_id == job_id)
                .order_by(GeneratedOutput.created_at.asc())
            )
        )
