from __future__ import annotations

from charset_normalizer import from_bytes

from preprocess_file.handlers.base import Handler
from preprocess_file.models import Document, Element, ElementType, FileKind, ProcessContext


class TextHandler(Handler):
    kinds = (FileKind.TXT, FileKind.MD, FileKind.JSON, FileKind.XML, FileKind.IPYNB)

    def process(self, ctx: ProcessContext) -> Document:
        kind = ctx.kind or FileKind.TXT
        raw = ctx.path.read_bytes()
        text, encoding = decode_bytes(raw)
        document = Document(
            source=str(ctx.path),
            file_type=kind,
            metadata={"encoding": encoding, "bytes": len(raw)},
        )
        if kind is FileKind.IPYNB:
            _add_notebook(document, text)
            return document
        if kind is FileKind.MD:
            _add_markdown(document, text)
            return document
        for block in _split_blocks(text):
            document.add(Element(type=ElementType.NARRATIVE, text=block))
        return document


def decode_bytes(raw: bytes) -> tuple[str, str]:
    if not raw:
        return "", "utf-8"
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    match = from_bytes(raw).best()
    if match is None:
        return raw.decode("utf-8", errors="replace"), "utf-8"
    return str(match), match.encoding or "utf-8"


def _split_blocks(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = [part.strip() for part in normalized.split("\n\n")]
    return [block for block in blocks if block]


def _add_markdown(document: Document, text: str) -> None:
    for line in text.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            hashes = len(stripped) - len(stripped.lstrip("#"))
            document.add(
                Element(
                    type=ElementType.TITLE,
                    text=stripped[hashes:].strip(),
                    metadata={"level": min(hashes, 6)},
                )
            )
        elif stripped.startswith(("- ", "* ", "+ ")):
            document.add(Element(type=ElementType.LIST, text=stripped[2:]))
        else:
            document.add(Element(type=ElementType.NARRATIVE, text=stripped))


def _add_notebook(document: Document, text: str) -> None:
    import json

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        document.warnings.append("Invalid notebook JSON; falling back to raw text.")
        document.add(Element(type=ElementType.NARRATIVE, text=text))
        return

    for index, cell in enumerate(payload.get("cells", [])):
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        source = str(source).strip()
        if not source:
            continue
        cell_type = cell.get("cell_type", "code")
        document.add(
            Element(
                type=ElementType.NARRATIVE,
                text=source,
                metadata={"cell_index": index, "cell_type": cell_type},
            )
        )
