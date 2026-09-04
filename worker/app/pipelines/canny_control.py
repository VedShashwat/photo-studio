from __future__ import annotations

from PIL import Image


def create_canny_control(
    image: Image.Image,
    alpha: Image.Image | None = None,
    low_threshold: int = 100,
    high_threshold: int = 200,
    include_luminance: bool = True,
) -> Image.Image:
    """Create a grayscale Canny map that includes the product alpha boundary."""
    if low_threshold < 0 or high_threshold <= low_threshold:
        raise ValueError("Canny thresholds must satisfy 0 <= low < high")

    if alpha is None and "A" in image.getbands():
        alpha = image.getchannel("A")
    if alpha is not None and alpha.size != image.size:
        raise ValueError("Alpha mask and image dimensions must match")

    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("OpenCV and NumPy are required for Canny preprocessing") from exc

    if not include_luminance and alpha is None:
        raise ValueError("An alpha mask is required when luminance edges are disabled")

    if include_luminance:
        rgb = np.asarray(image.convert("RGB"))
        grayscale = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(grayscale, low_threshold, high_threshold)
    else:
        edges = np.zeros((image.height, image.width), dtype=np.uint8)
    if alpha is not None:
        alpha_edges = cv2.Canny(np.asarray(alpha.convert("L")), low_threshold, high_threshold)
        edges = cv2.bitwise_or(edges, alpha_edges)
    return Image.fromarray(edges, mode="L")
