from __future__ import annotations

from preprocess_file.models import PageKind

# Heuristics aligned with production PDF routing:
# digital pages have real text blocks; scans are image-covered; hybrid has a weak OCR layer.
_MIN_TEXT_CHARS = 40
_TEXT_AREA_SCAN_MAX = 0.05
_IMAGE_AREA_SCAN_MIN = 0.50
_CID_RATIO_MAX = 0.08
_REPLACEMENT_RATIO_MAX = 0.02


def classify_pdf_page(page) -> PageKind:
    """Classify one PyMuPDF page as digital, scanned, hybrid, or empty."""
    page_area = abs(page.rect)
    if page_area <= 0:
        return PageKind.EMPTY

    text = page.get_text("text") or ""
    cleaned = "".join(ch for ch in text if ch.strip())
    text_area, image_area, cid_hits, replacement_hits, total_chars = _page_signals(page)

    text_ratio = text_area / page_area
    image_ratio = image_area / page_area
    cid_ratio = cid_hits / total_chars if total_chars else 0.0
    replacement_ratio = replacement_hits / total_chars if total_chars else 0.0
    garbled = cid_ratio >= _CID_RATIO_MAX or replacement_ratio >= _REPLACEMENT_RATIO_MAX

    if not cleaned and image_ratio < 0.08:
        return PageKind.EMPTY
    if garbled:
        return PageKind.HYBRID
    if len(cleaned) < _MIN_TEXT_CHARS and image_ratio >= _IMAGE_AREA_SCAN_MIN:
        return PageKind.SCANNED
    if text_ratio < _TEXT_AREA_SCAN_MAX and image_ratio >= _IMAGE_AREA_SCAN_MIN:
        return PageKind.HYBRID if len(cleaned) >= _MIN_TEXT_CHARS else PageKind.SCANNED
    if len(cleaned) < _MIN_TEXT_CHARS:
        return PageKind.SCANNED if image_ratio >= 0.2 else PageKind.EMPTY
    return PageKind.DIGITAL


def _page_signals(page) -> tuple[float, float, int, int, int]:
    raw = page.get_text("rawdict") or {}
    text_area = 0.0
    image_area = 0.0
    cid_hits = 0
    replacement_hits = 0
    total_chars = 0
    for block in raw.get("blocks", []):
        bbox = block.get("bbox") or [0, 0, 0, 0]
        area = max(0.0, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
        if block.get("type") == 1:
            image_area += area
            continue
        text_area += area
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                chunk = span.get("text") or ""
                total_chars += len(chunk)
                cid_hits += chunk.lower().count("(cid:")
                replacement_hits += chunk.count("\ufffd")
    return text_area, image_area, cid_hits, replacement_hits, total_chars
