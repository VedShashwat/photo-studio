import pytest
from PIL import Image

pytest.importorskip("cv2")
pytest.importorskip("numpy")

from app.pipelines.canny_control import create_canny_control


def test_canny_control_matches_image_dimensions_and_detects_alpha_boundary() -> None:
    image = Image.new("RGBA", (64, 48), (255, 0, 0, 0))
    for x in range(16, 48):
        for y in range(12, 36):
            image.putpixel((x, y), (255, 0, 0, 255))

    control = create_canny_control(image)

    assert control.mode == "L"
    assert control.size == image.size
    assert control.getbbox() is not None


def test_canny_control_rejects_mismatched_alpha_dimensions() -> None:
    image = Image.new("RGB", (64, 48), "white")

    with pytest.raises(ValueError, match="dimensions"):
        create_canny_control(image, Image.new("L", (32, 24), 255))


def test_canny_control_can_use_only_the_product_silhouette() -> None:
    image = Image.new("RGBA", (64, 48), (255, 255, 255, 255))
    alpha = Image.new("L", image.size, 0)
    for x in range(16, 48):
        for y in range(12, 36):
            alpha.putpixel((x, y), 255)

    control = create_canny_control(image, alpha=alpha, include_luminance=False)

    assert control.getbbox() is not None
    assert control.getpixel((32, 24)) == 0


def test_canny_control_requires_alpha_for_silhouette_only_mode() -> None:
    with pytest.raises(ValueError, match="alpha mask"):
        create_canny_control(Image.new("RGB", (32, 32)), include_luminance=False)
