import pytest
from PIL import Image

from app.pipelines.postprocessing import compose_product_canvas, composite_original_cutout, prepare_generation_canvas


def test_compose_product_canvas_is_centered_and_deterministic() -> None:
    cutout = Image.new("RGBA", (80, 40), (0, 0, 0, 0))
    for x in range(10, 70):
        for y in range(5, 35):
            cutout.putpixel((x, y), (255, 0, 0, 255))

    first = compose_product_canvas(cutout, canvas_size=1024, padding_ratio=0.12)
    second = compose_product_canvas(cutout, canvas_size=1024, padding_ratio=0.12)

    assert first.canvas.size == (1024, 1024)
    assert first.product_mask.size == (1024, 1024)
    assert first.bbox == second.bbox
    assert first.canvas.tobytes() == second.canvas.tobytes()
    assert first.product_mask.getbbox() == first.bbox


def test_composite_original_cutout_preserves_product_color() -> None:
    background = Image.new("RGB", (16, 16), "blue")
    cutout = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    cutout.putpixel((8, 8), (255, 0, 0, 255))

    result = composite_original_cutout(background, cutout, feather_radius=0)

    assert result.mode == "RGBA"
    assert result.getpixel((8, 8)) == (255, 0, 0, 255)
    assert result.getpixel((0, 0)) == (0, 0, 255, 255)


def test_prepare_generation_canvas_uses_product_free_scene_plate() -> None:
    cutout = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    cutout.putpixel((4, 4), (255, 0, 0, 255))

    result = prepare_generation_canvas(cutout)

    assert result.mode == "RGB"
    assert result.getpixel((0, 0)) == (48, 50, 53)
    assert result.getpixel((0, 7)) == (58, 53, 50)
    assert result.getpixel((4, 4)) != (255, 0, 0)


def test_prepare_generation_canvas_rejects_unknown_preset() -> None:
    with pytest.raises(ValueError, match="Unsupported scene preset"):
        prepare_generation_canvas(Image.new("RGBA", (8, 8)), "unknown")
