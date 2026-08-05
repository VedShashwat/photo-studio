import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import PromptHistory


class PromptHistoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, prompt_history: PromptHistory) -> PromptHistory:
        self.session.add(prompt_history)
        self.session.flush()
        return prompt_history

    def list_recent(self, page: int, limit: int) -> tuple[list[PromptHistory], int]:
        query = select(PromptHistory)
        total = self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        prompts = list(
            self.session.scalars(
                query.order_by(PromptHistory.created_at.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
        )
        return prompts, total
