from __future__ import annotations

import json
import zipfile
from pathlib import Path

from preprocess_file.models import FileKind

_EXT_MAP: dict[str, FileKind] = {
    ".pdf": FileKind.PDF,
    ".docx": FileKind.DOCX,
    ".doc": FileKind.DOC,
    ".pptx": FileKind.PPTX,
    ".ppt": FileKind.PPT,
    ".xlsx": FileKind.XLSX,
    ".xls": FileKind.XLS,
    ".csv": FileKind.CSV,
    ".tsv": FileKind.TSV,
    ".txt": FileKind.TXT,
    ".text": FileKind.TXT,
    ".log": FileKind.TXT,
    ".md": FileKind.MD,
    ".markdown": FileKind.MD,
    ".html": FileKind.HTML,
    ".htm": FileKind.HTML,
    ".xml": FileKind.XML,
    ".json": FileKind.JSON,
    ".png": FileKind.PNG,
    ".jpg": FileKind.JPEG,
    ".jpeg": FileKind.JPEG,
    ".webp": FileKind.WEBP,
    ".tif": FileKind.TIFF,
    ".tiff": FileKind.TIFF,
    ".bmp": FileKind.BMP,
    ".gif": FileKind.GIF,
    ".heic": FileKind.HEIC,
    ".eml": FileKind.EML,
    ".msg": FileKind.MSG,
    ".zip": FileKind.ZIP,
    ".epub": FileKind.EPUB,
    ".ipynb": FileKind.IPYNB,
    ".rtf": FileKind.RTF,
    ".wav": FileKind.AUDIO,
    ".mp3": FileKind.AUDIO,
    ".m4a": FileKind.AUDIO,
    ".flac": FileKind.AUDIO,
    ".aac": FileKind.AUDIO,
    ".mp4": FileKind.VIDEO,
    ".mkv": FileKind.VIDEO,
    ".mov": FileKind.VIDEO,
    ".avi": FileKind.VIDEO,
    ".webm": FileKind.VIDEO,
}

_TEXT_PREFIXES = (
    b"<!doctype html",
    b"<html",
    b"<?xml",
    b"{",
    b"[",
)


def detect(path: Path | str, sniff_bytes: int = 8192) -> FileKind:
    """Detect file kind using magic bytes first, then OOXML zip internals, then extension."""
    path = Path(path)
    header = path.read_bytes()[:sniff_bytes]
    magic_kind = _from_magic(header, path)
    if magic_kind is not None:
        return magic_kind

    ext_kind = _EXT_MAP.get(path.suffix.lower(), FileKind.UNKNOWN)
    if ext_kind is not FileKind.UNKNOWN:
        return ext_kind

    if _looks_like_text(header):
        return FileKind.TXT
    return FileKind.UNKNOWN


def _from_magic(header: bytes, path: Path) -> FileKind | None:
    if header.startswith(b"%PDF"):
        return FileKind.PDF
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return FileKind.PNG
    if header.startswith(b"\xff\xd8\xff"):
        return FileKind.JPEG
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return FileKind.WEBP
    if header.startswith(b"BM"):
        return FileKind.BMP
    if header.startswith((b"GIF87a", b"GIF89a")):
        return FileKind.GIF
    if header.startswith((b"II*\x00", b"MM\x00*")):
        return FileKind.TIFF
    if header.startswith(b"{\\rtf"):
        return FileKind.RTF
    if header.startswith(b"PK\x03\x04") or header.startswith(b"PK\x05\x06"):
        return _classify_zip_container(path)

    stripped = header.lstrip()
    lowered = stripped[:200].lower()
    if lowered.startswith((b"<!doctype html", b"<html")):
        return FileKind.HTML
    if lowered.startswith(b"<?xml"):
        return FileKind.XML
    if _looks_like_email(stripped):
        return FileKind.EML
    if stripped[:1] in (b"{", b"[") and _looks_like_json(path, stripped):
        if path.suffix.lower() == ".ipynb":
            return FileKind.IPYNB
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            payload = None
        if isinstance(payload, dict) and payload.get("nbformat") and "cells" in payload:
            return FileKind.IPYNB
        return FileKind.JSON
    return None


def _classify_zip_container(path: Path) -> FileKind:
    try:
        with zipfile.ZipFile(path) as archive:
            names = {info.filename.replace("\\", "/") for info in archive.infolist()}
    except zipfile.BadZipFile:
        return FileKind.ZIP

    if "word/document.xml" in names:
        return FileKind.DOCX
    if "xl/workbook.xml" in names:
        return FileKind.XLSX
    if "ppt/presentation.xml" in names:
        return FileKind.PPTX
    if "META-INF/container.xml" in names:
        return FileKind.EPUB
    if "mimetype" in names:
        try:
            with zipfile.ZipFile(path) as archive:
                mime = archive.read("mimetype").decode("utf-8", errors="ignore")
            if "epub" in mime:
                return FileKind.EPUB
        except Exception:
            pass
    return FileKind.ZIP


def _looks_like_email(header: bytes) -> bool:
    text = header.decode("utf-8", errors="ignore")
    lines = text.splitlines()[:12]
    keys = 0
    for line in lines:
        lower = line.lower()
        if lower.startswith(("from:", "to:", "subject:", "date:", "mime-version:", "received:")):
            keys += 1
    return keys >= 2


def _looks_like_json(path: Path, header: bytes) -> bool:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True
    except Exception:
        try:
            json.loads(header.decode("utf-8", errors="ignore") + "}")
        except Exception:
            return header.lstrip()[:1] in (b"{", b"[")
        return False


def _looks_like_text(header: bytes) -> bool:
    if not header:
        return True
    if b"\x00" in header:
        return False
    sample = header.decode("utf-8", errors="ignore")
    if not sample:
        return False
    printable = sum(1 for ch in sample if ch.isprintable() or ch in "\r\n\t")
    return printable / max(len(sample), 1) > 0.85
