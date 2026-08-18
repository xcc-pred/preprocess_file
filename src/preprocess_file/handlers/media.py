from __future__ import annotations

from preprocess_file.handlers.base import Handler
from preprocess_file.models import Document, Element, ElementType, FileKind, ProcessContext


class MediaHandler(Handler):
    """v1 stub: keep a stable interface for ASR/keyframe OCR without pulling Whisper."""

    kinds = (FileKind.AUDIO, FileKind.VIDEO)

    def process(self, ctx: ProcessContext) -> Document:
        kind = ctx.kind or FileKind.AUDIO
        document = Document(
            source=str(ctx.path),
            file_type=kind,
            metadata={"bytes": ctx.path.stat().st_size, "status": "not_transcribed"},
        )
        document.warnings.append(
            "Audio/video transcription is reserved for v2 (ffmpeg + ASR). "
            "The file was accepted and typed, but no transcript was produced."
        )
        document.add(
            Element(
                type=ElementType.METADATA,
                text=f"{kind.value} file {ctx.path.name} was detected but not transcribed.",
            )
        )
        return document
