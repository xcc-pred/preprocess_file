from __future__ import annotations

from pathlib import Path

import fitz

from preprocess_file.models import ElementType, FileKind, ProcessOptions
from preprocess_file.pdf_classify import classify_pdf_page
from preprocess_file.pipeline import process
from tests.fixtures import make_digital_pdf, make_scanned_pdf


def test_digital_pdf_extracts_text_layer(tmp_path: Path) -> None:
    path = make_digital_pdf(tmp_path / "digital.pdf")
    doc = process(path, ProcessOptions(ocr_enabled=False))
    assert doc.file_type is FileKind.PDF
    assert "native PDF text layer" in doc.text()
    assert doc.metadata["page_kinds"] == ["digital"]


def test_scanned_pdf_is_classified_scanned(tmp_path: Path) -> None:
    path = make_scanned_pdf(tmp_path / "scan.pdf")
    pdf = fitz.open(path)
    try:
        assert classify_pdf_page(pdf[0]).value == "scanned"
    finally:
        pdf.close()

    doc = process(path, ProcessOptions(ocr_enabled=False))
    assert doc.metadata["page_kinds"] == ["scanned"]
    assert any("OCR returned no text" in item or "No OCR" in item for item in doc.warnings) or any(
        element.type is ElementType.IMAGE for element in doc.elements
    )
