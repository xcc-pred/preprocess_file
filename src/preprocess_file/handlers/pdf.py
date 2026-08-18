from __future__ import annotations

from io import BytesIO

import fitz
from PIL import Image

from preprocess_file.errors import EncryptedFileError
from preprocess_file.handlers.base import Handler
from preprocess_file.models import Document, Element, ElementType, FileKind, PageKind, ProcessContext
from preprocess_file.ocr import ocr_image
from preprocess_file.pdf_classify import classify_pdf_page


class PdfHandler(Handler):
    kinds = (FileKind.PDF,)

    def process(self, ctx: ProcessContext) -> Document:
        document = Document(source=str(ctx.path), file_type=FileKind.PDF)
        pdf = fitz.open(ctx.path)
        try:
            if pdf.needs_pass:
                raise EncryptedFileError(f"Encrypted PDF: {ctx.path}")
            if pdf.page_count > ctx.options.max_pages:
                document.warnings.append(
                    f"PDF has {pdf.page_count} pages; only the first {ctx.options.max_pages} were processed."
                )
            page_kinds: list[str] = []
            for index, page in enumerate(pdf):
                if index >= ctx.options.max_pages:
                    break
                kind = classify_pdf_page(page)
                page_kinds.append(kind.value)
                if index > 0:
                    document.add(Element(type=ElementType.PAGE_BREAK, page=index + 1))
                if kind is PageKind.EMPTY:
                    continue
                if kind is PageKind.DIGITAL:
                    _extract_digital_page(document, page, index + 1)
                else:
                    _extract_ocr_page(document, page, index + 1, ctx, kind)
            document.metadata.update(
                {
                    "pages": pdf.page_count,
                    "processed_pages": min(pdf.page_count, ctx.options.max_pages),
                    "page_kinds": page_kinds,
                }
            )
        finally:
            pdf.close()
        return document


def _extract_digital_page(document: Document, page, page_number: int) -> None:
    data = page.get_text("dict") or {}
    sizes: list[float] = []
    blocks = []
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        spans = []
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = (span.get("text") or "").strip()
                if not text:
                    continue
                size = float(span.get("size") or 0)
                sizes.append(size)
                spans.append((size, text))
        if not spans:
            continue
        bbox = tuple(block.get("bbox") or (0, 0, 0, 0))
        text = " ".join(piece for _, piece in spans)
        avg_size = sum(size for size, _ in spans) / len(spans)
        blocks.append((bbox, avg_size, text))

    median = sorted(sizes)[len(sizes) // 2] if sizes else 0
    blocks.sort(key=lambda item: (round(item[0][1], 1), round(item[0][0], 1)))
    for bbox, avg_size, text in blocks:
        is_title = median and avg_size >= median * 1.3 and len(text) < 120
        document.add(
            Element(
                type=ElementType.TITLE if is_title else ElementType.NARRATIVE,
                text=text,
                page=page_number,
                bbox=bbox,
                metadata={"font_size": round(avg_size, 2), "level": 2} if is_title else {"font_size": round(avg_size, 2)},
            )
        )


def _extract_ocr_page(
    document: Document,
    page,
    page_number: int,
    ctx: ProcessContext,
    kind: PageKind,
) -> None:
    zoom = ctx.options.ocr_dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    text, confidence = ocr_image(image, ctx.options)
    if not text:
        document.warnings.append(
            f"Page {page_number} classified as {kind.value} but OCR returned no text."
        )
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        document.add(
            Element(
                type=ElementType.IMAGE,
                page=page_number,
                metadata={"page_kind": kind.value, "ocr_confidence": confidence},
            )
        )
        return
    document.add(
        Element(
            type=ElementType.NARRATIVE,
            text=text,
            page=page_number,
            metadata={"page_kind": kind.value, "ocr_confidence": confidence, "engine": "ocr"},
        )
    )
