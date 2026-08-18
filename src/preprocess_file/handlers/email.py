from __future__ import annotations

import email
from email import policy
from pathlib import Path
import tempfile

from preprocess_file.handlers.base import Handler
from preprocess_file.handlers.html import HtmlHandler
from preprocess_file.handlers.text import decode_bytes
from preprocess_file.models import Document, Element, ElementType, FileKind, ProcessContext
from preprocess_file.security import assert_depth


class EmailHandler(Handler):
    kinds = (FileKind.EML, FileKind.MSG)

    def process(self, ctx: ProcessContext) -> Document:
        kind = ctx.kind or FileKind.EML
        document = Document(source=str(ctx.path), file_type=kind)
        if kind is FileKind.MSG:
            document.warnings.append("Outlook .msg is not parsed natively in v1; export as .eml first.")
            return document

        raw = ctx.path.read_bytes()
        message = email.message_from_bytes(raw, policy=policy.default)
        headers = {
            "from": str(message.get("from", "")),
            "to": str(message.get("to", "")),
            "subject": str(message.get("subject", "")),
            "date": str(message.get("date", "")),
            "message_id": str(message.get("message-id", "")),
        }
        document.metadata["headers"] = headers
        if headers["subject"]:
            document.add(Element(type=ElementType.TITLE, text=headers["subject"], metadata={"level": 1}))
        summary = ", ".join(f"{key}: {value}" for key, value in headers.items() if value)
        if summary:
            document.add(Element(type=ElementType.METADATA, text=summary))

        body_added = False
        attachments: list[tuple[str, bytes]] = []
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_maintype() == "multipart":
                    continue
                filename = part.get_filename()
                payload = part.get_payload(decode=True) or b""
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition") or "")
                if filename or "attachment" in disposition.lower():
                    attachments.append((filename or f"attachment-{len(attachments)+1}", payload))
                    continue
                if not body_added and content_type == "text/plain":
                    text, _ = decode_bytes(payload)
                    if text.strip():
                        document.add(Element(type=ElementType.NARRATIVE, text=text.strip()))
                        body_added = True
                elif not body_added and content_type == "text/html":
                    _add_html_body(document, payload, ctx)
                    body_added = True
        else:
            payload = message.get_payload(decode=True) or b""
            if message.get_content_type() == "text/html":
                _add_html_body(document, payload, ctx)
            else:
                text, _ = decode_bytes(payload)
                if text.strip():
                    document.add(Element(type=ElementType.NARRATIVE, text=text.strip()))

        document.metadata["attachments"] = [name for name, _ in attachments]
        if not attachments or ctx.pipeline is None:
            return document

        with tempfile.TemporaryDirectory(prefix="preprocess-email-") as tmp:
            tmp_path = Path(tmp)
            for name, payload in attachments:
                safe_name = Path(name).name or "attachment"
                target = tmp_path / safe_name
                target.write_bytes(payload)
                child_ctx = ProcessContext(
                    path=target,
                    options=ctx.options,
                    depth=ctx.depth + 1,
                    pipeline=ctx.pipeline,
                )
                try:
                    assert_depth(child_ctx)
                    child = ctx.pipeline.process_context(child_ctx)
                    document.extend(child, prefix=f"attachment:{safe_name}")
                except Exception as exc:
                    document.warnings.append(f"Failed to process attachment {safe_name}: {exc}")
        return document


def _add_html_body(document: Document, payload: bytes, ctx: ProcessContext) -> None:
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as handle:
        handle.write(payload)
        path = Path(handle.name)
    try:
        nested = HtmlHandler().process(
            ProcessContext(path=path, options=ctx.options, depth=ctx.depth)
        )
        for element in nested.elements:
            if element.type is ElementType.TITLE and element.metadata.get("level") == 1:
                continue
            document.add(element)
    finally:
        path.unlink(missing_ok=True)
