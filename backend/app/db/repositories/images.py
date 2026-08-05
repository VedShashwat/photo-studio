import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Image


class ImageRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, image_id: uuid.UUID) -> Image | None:
        return self.session.scalar(select(Image).where(Image.id == image_id))

    def add(self, image: Image) -> Image:
        self.session.add(image)
        self.session.flush()
        return image
