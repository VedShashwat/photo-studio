from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.models import Image
from app.db.repositories.images import ImageRepository
from app.db.session import get_db
from app.schemas.images import ImageMetadataResponse, ImageUploadResponse
from app.schemas.jobs import BackgroundRemovalRequest, JobResponse
from app.services.image_service import InvalidImageError, validate_and_normalize
from app.services.job_service import JobService
from app.services.storage_service import StorageService

try:
    from shared.python.storage_paths import artifact_path
except ModuleNotFoundError:
    from shared.python.storage_paths import artifact_path


router = APIRouter(prefix="/images", tags=["images"])


def storage() -> StorageService:
    return StorageService(get_settings().storage_root)


def image_url(image_id: UUID, artifact: str) -> str:
    return f"/api/images/{image_id}/{artifact}"


@router.post("", response_model=ImageUploadResponse, status_code=201)
async def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)) -> ImageUploadResponse:
    content = await file.read()
    try:
        validated = validate_and_normalize(content, get_settings().max_upload_mb)
    except InvalidImageError as exc:
        status_code = 413 if exc.code == "FILE_TOO_LARGE" else 415 if exc.code == "UNSUPPORTED_MEDIA_TYPE" else 400
        raise AppError(exc.code, str(exc), status_code) from exc

    image_id = uuid4()
    original_path = artifact_path("originals", image_id, "png" if validated.mime_type == "image/png" else "jpg")
    storage().save_bytes(original_path, validated.content)
    image = Image(
        id=image_id,
        original_path=original_path,
        mime_type=validated.mime_type,
        width=validated.width,
        height=validated.height,
        file_size_bytes=len(validated.content),
        sha256=validated.sha256,
        status="uploaded",
        metadata_json={"client_filename": file.filename or "upload"},
    )
    ImageRepository(db).add(image)
    db.commit()
    return ImageUploadResponse(
        image_id=image.id,
        status=image.status,
        original_url=image_url(image.id, "original"),
        width=image.width,
        height=image.height,
        mime_type=image.mime_type,
    )


@router.get("/{image_id}", response_model=ImageMetadataResponse)
def get_image(image_id: UUID, db: Session = Depends(get_db)) -> ImageMetadataResponse:
    image = ImageRepository(db).get(image_id)
    if image is None:
        raise AppError("IMAGE_NOT_FOUND", "Image was not found.", 404)
    return ImageMetadataResponse(
        image_id=image.id,
        status=image.status,
        original_url=image_url(image.id, "original"),
        mask_url=image_url(image.id, "mask") if image.mask_path else None,
        cutout_url=image_url(image.id, "cutout") if image.cutout_path else None,
        width=image.width,
        height=image.height,
        mime_type=image.mime_type,
        metadata=image.metadata_json or {},
    )


@router.post("/{image_id}/remove-background", response_model=JobResponse, status_code=202)
def request_background_removal(
    image_id: UUID,
    request: BackgroundRemovalRequest | None = None,
    db: Session = Depends(get_db),
) -> JobResponse:
    return JobService(db).request_background_removal(image_id, force=request.force if request else False)


def stream_artifact(image_id: UUID, artifact: str, db: Session) -> FileResponse:
    image = ImageRepository(db).get(image_id)
    if image is None:
        raise AppError("IMAGE_NOT_FOUND", "Image was not found.", 404)
    relative_path = image.original_path if artifact == "original" else image.mask_path if artifact == "mask" else image.cutout_path
    if not relative_path:
        raise AppError("IMAGE_NOT_READY", f"The {artifact} artifact is not ready.", 409)
    try:
        path = storage().open_path(relative_path)
    except FileNotFoundError as exc:
        raise AppError("FILE_NOT_FOUND", "The stored image file is missing.", 404) from exc
    media_type = "image/png" if artifact in {"mask", "cutout"} else image.mime_type
    return FileResponse(path, media_type=media_type)


@router.get("/{image_id}/original")
def get_original(image_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    return stream_artifact(image_id, "original", db)


@router.get("/{image_id}/mask")
def get_mask(image_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    return stream_artifact(image_id, "mask", db)


@router.get("/{image_id}/cutout")
def get_cutout(image_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    return stream_artifact(image_id, "cutout", db)
