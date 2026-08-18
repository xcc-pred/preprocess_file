from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class FileKind(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    PPTX = "pptx"
    PPT = "ppt"
    XLSX = "xlsx"
    XLS = "xls"
    CSV = "csv"
    TSV = "tsv"
    TXT = "txt"
    MD = "md"
    HTML = "html"
    XML = "xml"
    JSON = "json"
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"
    TIFF = "tiff"
    BMP = "bmp"
    GIF = "gif"
    HEIC = "heic"
    EML = "eml"
    MSG = "msg"
    ZIP = "zip"
    EPUB = "epub"
    IPYNB = "ipynb"
    RTF = "rtf"
    AUDIO = "audio"
    VIDEO = "video"
    UNKNOWN = "unknown"


class ElementType(str, Enum):
    TITLE = "title"
    NARRATIVE = "narrative"
    LIST = "list"
    TABLE = "table"
    IMAGE = "image"
    FORMULA = "formula"
    PAGE_BREAK = "page_break"
    METADATA = "metadata"
    TRANSCRIPT = "transcript"


class PageKind(str, Enum):
    DIGITAL = "digital"
    SCANNED = "scanned"
    HYBRID = "hybrid"
    EMPTY = "empty"


IMAGE_KINDS = {
    FileKind.PNG,
    FileKind.JPEG,
    FileKind.WEBP,
    FileKind.TIFF,
    FileKind.BMP,
    FileKind.GIF,
    FileKind.HEIC,
}

SPREADSHEET_KINDS = {FileKind.XLSX, FileKind.XLS, FileKind.CSV, FileKind.TSV}


@dataclass
class ProcessOptions:
    max_bytes: int = 100 * 1024 * 1024
    max_pages: int = 500
    max_zip_members: int = 200
    max_zip_uncompressed: int = 500 * 1024 * 1024
    max_recursion: int = 3
    ocr_enabled: bool = True
    ocr_dpi: int = 300
    ocr_lang: str = "chi_sim+eng"
    image_preprocess: bool = True
    include_headers_footers: bool = False
    include_comments: bool = False
    spreadsheet_forward_fill: bool = True
    extract_images: bool = True


@dataclass
class Element:
    type: ElementType
    text: str = ""
    page: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": self.type.value,
            "text": self.text,
        }
        if self.page is not None:
            payload["page"] = self.page
        if self.bbox is not None:
            payload["bbox"] = list(self.bbox)
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


@dataclass
class Document:
    source: str
    file_type: FileKind
    elements: list[Element] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def add(self, element: Element) -> None:
        self.elements.append(element)

    def extend(self, other: Document, *, prefix: str | None = None) -> None:
        for warning in other.warnings:
            self.warnings.append(f"{prefix}: {warning}" if prefix else warning)
        for element in other.elements:
            cloned = Element(
                type=element.type,
                text=element.text,
                page=element.page,
                bbox=element.bbox,
                metadata={**element.metadata},
            )
            if prefix:
                cloned.metadata.setdefault("parent", prefix)
            self.elements.append(cloned)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "file_type": self.file_type.value,
            "metadata": self.metadata,
            "warnings": self.warnings,
            "elements": [element.to_dict() for element in self.elements],
        }

    def to_markdown(self) -> str:
        from preprocess_file.output import document_to_markdown

        return document_to_markdown(self)

    def text(self) -> str:
        parts = [element.text.strip() for element in self.elements if element.text.strip()]
        return "\n\n".join(parts)


@dataclass
class ProcessContext:
    path: Path
    options: ProcessOptions
    depth: int = 0
    kind: FileKind | None = None
    pipeline: Any = None
