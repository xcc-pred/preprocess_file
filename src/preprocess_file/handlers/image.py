from __future__ import annotations

from PIL import Image, ImageSequence

from preprocess_file.handlers.base import Handler
from preprocess_file.models import IMAGE_KINDS, Document, Element, ElementType, FileKind, ProcessContext
from preprocess_file.ocr import ocr_image


class ImageHandler(Handler):
    kinds = tuple(IMAGE_KINDS)

    def process(self, ctx: ProcessContext) -> Document:
        kind = ctx.kind or FileKind.PNG
        document = Document(source=str(ctx.path), file_type=kind)
        with Image.open(ctx.path) as image:
            document.metadata.update(
                {
                    "width": image.width,
                    "height": image.height,
                    "mode": image.mode,
                    "format": image.format,
                    "frames": getattr(image, "n_frames", 1),
                }
            )
            frames = [image.copy()]
            if getattr(image, "n_frames", 1) > 1:
                frames = [frame.copy() for frame in ImageSequence.Iterator(image)]
        for index, frame in enumerate(frames, start=1):
            rgb = frame.convert("RGB")
            text, confidence = ocr_image(rgb, ctx.options)
            if len(frames) > 1:
                document.add(Element(type=ElementType.PAGE_BREAK, page=index))
            document.add(
                Element(
                    type=ElementType.IMAGE if not text else ElementType.NARRATIVE,
                    text=text,
                    page=index if len(frames) > 1 else None,
                    metadata={"ocr_confidence": confidence, "frame": index},
                )
            )
            if not text:
                document.warnings.append(
                    f"No OCR text from frame {index}. Install tesseract + preprocess-file[ocr] for scanned images."
                )
        return document
