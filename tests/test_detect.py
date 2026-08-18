from __future__ import annotations

from pathlib import Path
import zipfile

from preprocess_file.detect import detect
from preprocess_file.models import FileKind


def test_detect_pdf_magic(tmp_path: Path) -> None:
    path = tmp_path / "a.bin"
    path.write_bytes(b"%PDF-1.7\n%")
    assert detect(path) is FileKind.PDF


def test_detect_docx_inside_zip(tmp_path: Path) -> None:
    path = tmp_path / "report.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", "<w:document />")
        archive.writestr("[Content_Types].xml", "<Types />")
    assert detect(path) is FileKind.DOCX


def test_detect_plain_zip(tmp_path: Path) -> None:
    path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("readme.txt", "hello")
    assert detect(path) is FileKind.ZIP


def test_detect_jpeg_magic(tmp_path: Path) -> None:
    path = tmp_path / "photo.bin"
    path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 20)
    assert detect(path) is FileKind.JPEG


def test_detect_email_headers(tmp_path: Path) -> None:
    path = tmp_path / "mail.txt"
    path.write_text("From: a@x.com\nTo: b@x.com\nSubject: Hi\n\nbody\n", encoding="utf-8")
    assert detect(path) is FileKind.EML
