from __future__ import annotations

from pathlib import Path

from PIL import Image

from preprocess_file.image_prep import preprocess_for_ocr
from preprocess_file.models import ProcessOptions


def ocr_image(image: Image.Image, options: ProcessOptions) -> tuple[str, float | None]:
    """Return (text, mean_confidence). Confidence is None when engine has no scores."""
    if not options.ocr_enabled:
        return "", None

    prepared = preprocess_for_ocr(image) if options.image_preprocess else ImageOps_grayscale(image)

    try:
        import pytesseract
    except ImportError:
        return "", None

    try:
        from pytesseract import Output
    except Exception:
        Output = None  # type: ignore[assignment]

    try:
        if Output is not None:
            data = pytesseract.image_to_data(
                prepared,
                lang=_tesseract_lang(options.ocr_lang),
                output_type=Output.DICT,
            )
            texts = [word for word in data.get("text", []) if word and word.strip()]
            confs = [
                float(conf)
                for conf, word in zip(data.get("conf", []), data.get("text", []))
                if word and word.strip() and float(conf) >= 0
            ]
            text = " ".join(texts).strip()
            mean = sum(confs) / len(confs) if confs else None
            return text, mean
        text = pytesseract.image_to_string(prepared, lang=_tesseract_lang(options.ocr_lang))
        return text.strip(), None
    except Exception:
        try:
            text = pytesseract.image_to_string(prepared)
            return text.strip(), None
        except Exception:
            return "", None


def ocr_path(path: Path, options: ProcessOptions) -> tuple[str, float | None]:
    with Image.open(path) as image:
        return ocr_image(image.convert("RGB"), options)


def tesseract_available() -> bool:
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _tesseract_lang(lang: str) -> str:
    # Keep a fallback that works on default English-only installs.
    return lang or "eng"


def ImageOps_grayscale(image: Image.Image) -> Image.Image:
    from PIL import ImageOps

    return ImageOps.grayscale(ImageOps.exif_transpose(image))
