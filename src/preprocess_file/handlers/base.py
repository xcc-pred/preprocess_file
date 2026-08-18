from __future__ import annotations

from abc import ABC, abstractmethod

from preprocess_file.models import Document, FileKind, ProcessContext


class Handler(ABC):
    kinds: tuple[FileKind, ...] = ()

    @abstractmethod
    def process(self, ctx: ProcessContext) -> Document:
        raise NotImplementedError
