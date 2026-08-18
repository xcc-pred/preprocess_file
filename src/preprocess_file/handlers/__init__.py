from __future__ import annotations

from preprocess_file.handlers.archive import ArchiveHandler
from preprocess_file.handlers.email import EmailHandler
from preprocess_file.handlers.html import HtmlHandler
from preprocess_file.handlers.image import ImageHandler
from preprocess_file.handlers.media import MediaHandler
from preprocess_file.handlers.pdf import PdfHandler
from preprocess_file.handlers.ppt import PptHandler
from preprocess_file.handlers.spreadsheet import SpreadsheetHandler
from preprocess_file.handlers.text import TextHandler
from preprocess_file.handlers.word import WordHandler
from preprocess_file.models import FileKind

_HANDLERS = [
    PdfHandler(),
    WordHandler(),
    PptHandler(),
    SpreadsheetHandler(),
    ImageHandler(),
    HtmlHandler(),
    EmailHandler(),
    ArchiveHandler(),
    TextHandler(),
    MediaHandler(),
]


def get_handler(kind: FileKind):
    for handler in _HANDLERS:
        if kind in handler.kinds:
            return handler
    return None
