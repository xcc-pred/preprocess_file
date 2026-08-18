from __future__ import annotations

from preprocess_file.models import Document, Element, ElementType


def document_to_markdown(document: Document) -> str:
    parts: list[str] = []
    for element in document.elements:
        if element.type is ElementType.PAGE_BREAK:
            parts.append("\n---\n")
            continue
        if not element.text.strip() and element.type is not ElementType.IMAGE:
            continue
        if element.type is ElementType.TITLE:
            level = int(element.metadata.get("level", 1))
            level = min(max(level, 1), 6)
            parts.append(f"{'#' * level} {element.text.strip()}")
        elif element.type is ElementType.TABLE:
            parts.append(element.text.strip())
        elif element.type is ElementType.IMAGE:
            caption = element.text.strip() or element.metadata.get("caption") or "image"
            parts.append(f"![{caption}]({element.metadata.get('path', '')})".rstrip("()"))
            if element.text.strip():
                parts.append(element.text.strip())
        elif element.type is ElementType.LIST:
            for line in element.text.splitlines():
                stripped = line.strip()
                if stripped:
                    parts.append(f"- {stripped.lstrip('-•* ')}")
        elif element.type is ElementType.TRANSCRIPT:
            stamp = element.metadata.get("start")
            prefix = f"[{stamp}] " if stamp is not None else ""
            parts.append(f"{prefix}{element.text.strip()}")
        else:
            parts.append(element.text.strip())
    body = "\n\n".join(part for part in parts if part.strip())
    warning_block = ""
    if document.warnings:
        warning_block = "\n\n".join(f"> warning: {item}" for item in document.warnings)
        return f"{body}\n\n{warning_block}".strip()
    return body


def table_to_markdown(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    normalized = [_pad_row(row, width) for row in rows]
    header = normalized[0]
    body = normalized[1:] or [[""] * width]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _pad_row(row: list[str], width: int) -> list[str]:
    values = [str(cell).replace("\n", "<br>").strip() if cell is not None else "" for cell in row]
    if len(values) < width:
        values.extend([""] * (width - len(values)))
    return values[:width]
