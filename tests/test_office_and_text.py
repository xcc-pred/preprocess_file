from __future__ import annotations

from pathlib import Path

from preprocess_file.models import ElementType, FileKind, ProcessOptions
from preprocess_file.pipeline import process
from tests.fixtures import make_docx, make_html, make_pptx, make_xlsx, write_text


def test_text_gbk_decoding(tmp_path: Path) -> None:
    path = write_text(tmp_path / "note.txt", "这是一段用于编码探测的中文内容，重复多次。\n" * 8, encoding="gbk")
    doc = process(path)
    assert "中文内容" in doc.text()
    assert doc.metadata["encoding"].lower().startswith("gb")


def test_markdown_headings(tmp_path: Path) -> None:
    path = write_text(tmp_path / "guide.md", "# Title\n\nHello\n")
    doc = process(path)
    assert doc.elements[0].type is ElementType.TITLE
    assert doc.elements[0].text == "Title"


def test_html_strips_noise_and_keeps_table(tmp_path: Path) -> None:
    path = make_html(tmp_path / "page.html")
    doc = process(path)
    text = doc.text()
    assert "Main Story" in text
    assert "Visible paragraph" in text
    assert "unsubscribe" not in text
    assert "alert" not in text
    assert any(element.type is ElementType.TABLE for element in doc.elements)


def test_docx_heading_and_table(tmp_path: Path) -> None:
    path = make_docx(tmp_path / "review.docx")
    doc = process(path)
    assert doc.file_type is FileKind.DOCX
    titles = [element.text for element in doc.elements if element.type is ElementType.TITLE]
    assert "Quarterly Review" in titles
    tables = [element.text for element in doc.elements if element.type is ElementType.TABLE]
    assert tables and "License" in tables[0]


def test_pptx_includes_notes(tmp_path: Path) -> None:
    path = make_pptx(tmp_path / "deck.pptx")
    doc = process(path)
    assert "Launch Plan" in doc.text()
    assert "OCR routing" in doc.text()


def test_xlsx_detects_header_and_fills_merged_cells(tmp_path: Path) -> None:
    path = make_xlsx(tmp_path / "sales.xlsx")
    doc = process(path, ProcessOptions(spreadsheet_forward_fill=True))
    table = next(element for element in doc.elements if element.type is ElementType.TABLE)
    assert table.metadata["header_row"] == 3
    assert table.text.count("North") >= 2
    assert "Widget" in table.text
