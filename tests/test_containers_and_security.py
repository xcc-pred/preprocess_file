from __future__ import annotations

from pathlib import Path
import zipfile

import pytest

from preprocess_file.errors import FileTooLargeError, UnsafeArchiveError, UnsupportedTypeError
from preprocess_file.models import FileKind, ProcessOptions
from preprocess_file.pipeline import process
from tests.fixtures import make_eml_with_attachment, make_zip, write_text


def test_email_recurses_into_attachment(tmp_path: Path) -> None:
    note = write_text(tmp_path / "note.txt", "Attachment secret")
    eml = make_eml_with_attachment(tmp_path / "mail.eml", note)
    doc = process(eml)
    assert doc.file_type is FileKind.EML
    assert "Please review" in doc.text()
    assert "Attachment secret" in doc.text()


def test_zip_recurses_members(tmp_path: Path) -> None:
    inner = write_text(tmp_path / "inner.md", "# Nested\n\nBody")
    archive = make_zip(tmp_path / "bundle.zip", {"docs/inner.md": inner})
    doc = process(archive)
    assert "Nested" in doc.text()
    assert "Body" in doc.text()


def test_zip_slip_is_rejected(tmp_path: Path) -> None:
    archive_path = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        info = zipfile.ZipInfo("../escape.txt")
        archive.writestr(info, "nope")
    with pytest.raises(UnsafeArchiveError):
        process(archive_path)


def test_file_too_large(tmp_path: Path) -> None:
    path = write_text(tmp_path / "big.txt", "hello")
    with pytest.raises(FileTooLargeError):
        process(path, ProcessOptions(max_bytes=1))


def test_unknown_binary_rejected(tmp_path: Path) -> None:
    path = tmp_path / "blob.bin"
    path.write_bytes(b"\x00\x01\x02\x03\x04")
    with pytest.raises(UnsupportedTypeError):
        process(path)
