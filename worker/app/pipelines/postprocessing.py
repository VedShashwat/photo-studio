from dataclasses import dataclass

from PIL import Image, ImageFilter, ImageOps


SCENE_PLATE_COLORS: dict[str, tuple[tuple[int, int, int], tuple[int, int, int], float]] = {
    "white_amazon": ((252, 252, 251), (246, 247, 246), 0.82),
    "luxury_studio": ((38, 40, 43), (72, 67, 64), 0.72),
    "wooden_table": ((190, 169, 142), (116, 76, 45), 0.68),
    "coffee_shop": ((91, 67, 52), (132, 88, 54), 0.67),
    "office_desk": ((224, 230, 230), (151, 128, 105), 0.69),
    "marble_surface": ((248, 248, 246), (216, 219, 218), 0.70),
    "outdoor_lifestyle": ((164, 190, 174), (111, 137, 99), 0.68),
}


class MaskQualityError(ValueError):
    pass


@dataclass(frozen=True)
class MaskMetrics:
    coverage: float
    bbox: tuple[int, int, int, int] | None


@dataclass(frozen=True)
class CanvasComposition:
    canvas: Image.Image
    product_mask: Image.Image
    bbox: tuple[int, int, int, int]


def compose_product_canvas(
    cutout: Image.Image,
    canvas_size: int = 1024,
    padding_ratio: float = 0.18,
) -> CanvasComposition:
    """Center a cutout on a transparent square canvas with deterministic padding."""
    if canvas_size <= 0:
        raise ValueError("Canvas size must be positive")
    if not 0 <= padding_ratio < 0.5:
        raise ValueError("Padding ratio must be between 0 and 0.5")

    source = cutout.convert("RGBA")
    source_bbox = source.getchannel("A").getbbox()
    if source_bbox is None:
        raise MaskQualityError("Cutout does not contain a foreground product")
    cropped = source.crop(source_bbox)
    max_dimension = max(1, int(canvas_size * (1 - 2 * padding_ratio)))
    scale = min(max_dimension / cropped.width, max_dimension / cropped.height)
    resized_size = (
        max(1, round(cropped.width * scale)),
        max(1, round(cropped.height * scale)),
    )
    resized = cropped.resize(resized_size, Image.Resampling.LANCZOS)
    left = (canvas_size - resized.width) // 2
    top = (canvas_size - resized.height) // 2
    bbox = (left, top, left + resized.width, top + resized.height)

    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    canvas.alpha_composite(resized, dest=(left, top))
    product_mask = Image.new("L", (canvas_size, canvas_size), 0)
    product_mask.paste(resized.getchannel("A"), (left, top))
    return CanvasComposition(canvas=canvas, product_mask=product_mask, bbox=bbox)


def prepare_generation_canvas(
    cutout_canvas: Image.Image,
    scene_preset: str = "luxury_studio",
) -> Image.Image:
    """Build a product-free two-plane seed plate for background generation."""
    if scene_preset not in SCENE_PLATE_COLORS:
        raise ValueError(f"Unsupported scene preset '{scene_preset}'")
    wall_color, surface_color, horizon_ratio = SCENE_PLATE_COLORS[scene_preset]
    width, height = cutout_canvas.size
    horizon = max(1, min(height - 1, round(height * horizon_ratio)))

    wall_gradient = Image.linear_gradient("L").resize((width, horizon))
    wall = ImageOps.colorize(
        wall_gradient,
        black=tuple(min(255, channel + 12) for channel in wall_color),
        white=wall_color,
    )
    surface_gradient = Image.linear_gradient("L").resize((width, height - horizon))
    surface = ImageOps.colorize(
        surface_gradient,
        black=surface_color,
        white=tuple(max(0, channel - 18) for channel in surface_color),
    )
    background = Image.new("RGB", (width, height))
    background.paste(wall, (0, 0))
    background.paste(surface, (0, horizon))
    return background


def refine_mask(mask: Image.Image) -> tuple[Image.Image, MaskMetrics]:
    """Threshold, clean, and feather a foreground probability mask."""
    binary = mask.convert("L").point(lambda value: 255 if value >= 128 else 0)
    binary = binary.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    coverage = sum(count for value, count in enumerate(binary.histogram()) if value >= 128) / (
        binary.width * binary.height
    )
    bbox = binary.getbbox()
    if coverage < 0.02 or coverage > 0.95 or bbox is None:
        raise MaskQualityError(f"Suspicious foreground coverage: {coverage:.3f}")
    feathered = binary.filter(ImageFilter.GaussianBlur(radius=1.2))
    return feathered, MaskMetrics(coverage=coverage, bbox=bbox)


def composite_original_cutout(
    background: Image.Image,
    cutout: Image.Image,
    feather_radius: float = 1.2,
) -> Image.Image:
    """Place the original product pixels over a generated background."""
    if background.size != cutout.size:
        raise ValueError("Background and cutout dimensions must match")
    if feather_radius < 0:
        raise ValueError("Feather radius must be non-negative")

    foreground = cutout.convert("RGBA")
    if feather_radius:
        foreground.putalpha(foreground.getchannel("A").filter(ImageFilter.GaussianBlur(feather_radius)))
    result = background.convert("RGBA")
    result.alpha_composite(foreground)
    return result
