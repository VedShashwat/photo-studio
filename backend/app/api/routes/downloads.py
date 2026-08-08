from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.repositories.outputs import OutputRepository
from app.db.session import get_db
from app.services.storage_service import StorageService


router = APIRouter(prefix="/outputs", tags=["outputs"])


def storage() -> StorageService:
    return StorageService(get_settings().storage_root)


def stream_output(output_id: UUID, *, download: bool, db: Session) -> FileResponse:
    output = OutputRepository(db).get(output_id)
    if output is None:
        raise AppError("OUTPUT_NOT_FOUND", "Output was not found.", 404)
    if output.status != "succeeded":
        raise AppError("OUTPUT_NOT_READY", "The output is not ready.", 409)
    try:
        path = storage().open_path(output.output_path)
    except FileNotFoundError as exc:
        raise AppError("FILE_NOT_FOUND", "The stored output file is missing.", 404) from exc
    return FileResponse(
        path,
        media_type="image/png",
        filename=f"output-{output.id}.png" if download else None,
    )


@router.get("/{output_id}/image")
def get_output_image(output_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    return stream_output(output_id, download=False, db=db)


@router.get("/{output_id}/download")
def download_output(output_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    return stream_output(output_id, download=True, db=db)
