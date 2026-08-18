from __future__ import annotations

from pathlib import Path

from preprocess_file.detect import detect
from preprocess_file.errors import UnsupportedTypeError
from preprocess_file.handlers import get_handler
from preprocess_file.models import Document, FileKind, ProcessContext, ProcessOptions
from preprocess_file.security import assert_size


class Pipeline:
    def __init__(self, options: ProcessOptions | None = None) -> None:
        self.options = options or ProcessOptions()

    def process(self, path: str | Path) -> Document:
        ctx = ProcessContext(path=Path(path), options=self.options, pipeline=self)
        return self.process_context(ctx)

    def process_context(self, ctx: ProcessContext) -> Document:
        ctx.pipeline = self
        assert_size(ctx.path, ctx.options)
        kind = ctx.kind or detect(ctx.path)
        ctx.kind = kind
        handler = get_handler(kind)
        if handler is None or kind is FileKind.UNKNOWN:
            raise UnsupportedTypeError(f"Unsupported file type for {ctx.path}")
        document = handler.process(ctx)
        document.metadata.setdefault("detected_type", kind.value)
        document.metadata.setdefault("depth", ctx.depth)
        return document


def process(path: str | Path, options: ProcessOptions | None = None) -> Document:
    return Pipeline(options).process(path)
