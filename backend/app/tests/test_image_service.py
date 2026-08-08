from io import BytesIO

import pytest
from PIL import Image

from app.services.image_service import InvalidImageError, validate_and_normalize


def image_bytes(image_format: str = "JPEG", size: tuple[int, int] = (640, 512)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, "white").save(buffer, format=image_format)
    return buffer.getvalue()


def test_validate_and_normalize_returns_metadata() -> None:
    result = validate_and_normalize(image_bytes(), max_upload_mb=1)
    assert result.mime_type == "image/jpeg"
    assert (result.width, result.height) == (640, 512)
    assert len(result.sha256) == 64


def test_validate_rejects_images_below_minimum_resolution() -> None:
    with pytest.raises(InvalidImageError, match="dimensions"):
        validate_and_normalize(image_bytes(size=(511, 512)), max_upload_mb=1)
