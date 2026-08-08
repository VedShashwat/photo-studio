from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO

from PIL import Image, ImageOps


ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
MIN_DIMENSION = 512
MAX_DIMENSION = 8192


class InvalidImageError(ValueError):
    def __init__(self, message: str, code: str = "INVALID_IMAGE"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ValidatedImage:
    content: bytes
    mime_type: str
    width: int
    height: int
    sha256: str


def validate_and_normalize(content: bytes, max_upload_mb: int) -> ValidatedImage:
    max_bytes = max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise InvalidImageError(f"Image must be smaller than {max_upload_mb} MB.", "FILE_TOO_LARGE")
    if not content:
        raise InvalidImageError("Image file is empty.")

    try:
        with Image.open(BytesIO(content)) as source:
            image_format = source.format
            if image_format not in ALLOWED_FORMATS:
                raise InvalidImageError("Only JPEG, PNG, and WebP images are supported.", "UNSUPPORTED_MEDIA_TYPE")
            image = ImageOps.exif_transpose(source)
            width, height = image.size
            if min(width, height) < MIN_DIMENSION or max(width, height) > MAX_DIMENSION:
                raise InvalidImageError(
                    f"Image dimensions must be between {MIN_DIMENSION} and {MAX_DIMENSION} pixels.",
                    "INVALID_IMAGE_DIMENSIONS",
                )
            if "A" in image.getbands():
                normalized = image.convert("RGBA")
                output_format = "PNG"
            else:
                normalized = image.convert("RGB")
                output_format = "JPEG"
            buffer = BytesIO()
            normalized.save(buffer, format=output_format, quality=95, optimize=True)
    except InvalidImageError:
        raise
    except Exception as exc:
        raise InvalidImageError("The uploaded file is not a readable image.") from exc

    normalized_content = buffer.getvalue()
    return ValidatedImage(
        content=normalized_content,
        mime_type=ALLOWED_FORMATS[output_format],
        width=width,
        height=height,
        sha256=sha256(normalized_content).hexdigest(),
    )
