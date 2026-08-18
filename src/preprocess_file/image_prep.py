from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image, ImageFilter, ImageOps


def preprocess_for_ocr(image: Image.Image, *, target_min_side: int = 1600) -> Image.Image:
    """Normalize a document image before OCR.

    Order: EXIF orientation -> grayscale -> upscale -> deskew -> denoise -> contrast.
    Binarization is left to the OCR engine unless contrast is extremely low.
    """
    image = ImageOps.exif_transpose(image)
    if image.mode not in {"L", "RGB", "RGBA"}:
        image = image.convert("RGB")
    gray = ImageOps.grayscale(image)
    gray = _upscale(gray, target_min_side)
    gray = deskew(gray)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    gray = ImageOps.autocontrast(gray)
    return gray


def deskew(image: Image.Image, max_angle: float = 15.0) -> Image.Image:
    """Deskew using horizontal projection profiles; no-op if angle is tiny."""
    angle = estimate_skew_angle(image, max_angle=max_angle)
    if abs(angle) < 0.4:
        return image
    return image.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor=255, expand=True)


def estimate_skew_angle(image: Image.Image, max_angle: float = 15.0) -> float:
    arr = np.asarray(ImageOps.invert(image.convert("L")))
    if arr.size == 0:
        return 0.0
    # Downsample for speed.
    scale = max(arr.shape) / 800.0
    if scale > 1:
        arr = arr[:: int(scale), :: int(scale)]
    binary = arr > np.mean(arr)
    best_angle = 0.0
    best_score = -1.0
    for angle in np.linspace(-max_angle, max_angle, 61):
        rotated = _rotate_binary(binary, angle)
        projection = rotated.sum(axis=1).astype(np.float64)
        score = float(np.var(projection))
        if score > best_score:
            best_score = score
            best_angle = float(angle)
    return best_angle


def render_image_bytes(image: Image.Image, fmt: str = "PNG") -> bytes:
    buffer = BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


def _upscale(image: Image.Image, target_min_side: int) -> Image.Image:
    width, height = image.size
    shortest = min(width, height)
    if shortest >= target_min_side:
        return image
    factor = target_min_side / max(shortest, 1)
    new_size = (max(1, int(width * factor)), max(1, int(height * factor)))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def _rotate_binary(binary: np.ndarray, angle: float) -> np.ndarray:
    image = Image.fromarray((binary * 255).astype(np.uint8))
    rotated = image.rotate(angle, resample=Image.Resampling.NEAREST, fillcolor=0, expand=True)
    return np.asarray(rotated) > 127
