from __future__ import annotations

from bs4 import BeautifulSoup, NavigableString, Tag

from preprocess_file.handlers.base import Handler
from preprocess_file.handlers.text import decode_bytes
from preprocess_file.models import Document, Element, ElementType, FileKind, ProcessContext
from preprocess_file.output import table_to_markdown

_NOISE_TAGS = {"script", "style", "nav", "footer", "aside", "form", "iframe", "noscript"}


class HtmlHandler(Handler):
    kinds = (FileKind.HTML,)

    def process(self, ctx: ProcessContext) -> Document:
        raw = ctx.path.read_bytes()
        html, encoding = decode_bytes(raw)
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(_NOISE_TAGS):
            tag.decompose()
        if soup.header and not ctx.options.include_headers_footers:
            soup.header.decompose()

        root = soup.find("article") or soup.find("main") or soup.body or soup
        title = soup.title.get_text(" ", strip=True) if soup.title else ctx.path.stem
        document = Document(
            source=str(ctx.path),
            file_type=FileKind.HTML,
            metadata={"encoding": encoding, "title": title},
        )
        if title:
            document.add(Element(type=ElementType.TITLE, text=title, metadata={"level": 1}))
        _walk(root, document)
        return document


def _walk(node: Tag | NavigableString | None, document: Document) -> None:
    if node is None:
        return
    if isinstance(node, NavigableString):
        return
    name = node.name.lower() if node.name else ""
    if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        document.add(
            Element(
                type=ElementType.TITLE,
                text=node.get_text(" ", strip=True),
                metadata={"level": int(name[1])},
            )
        )
        return
    if name == "table":
        rows = []
        for tr in node.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["th", "td"])]
            if any(cells):
                rows.append(cells)
        markdown = table_to_markdown(rows)
        if markdown:
            document.add(Element(type=ElementType.TABLE, text=markdown, metadata={"rows": len(rows)}))
        return
    if name in {"ul", "ol"}:
        items = [li.get_text(" ", strip=True) for li in node.find_all("li", recursive=False)]
        items = [item for item in items if item]
        if items:
            document.add(Element(type=ElementType.LIST, text="\n".join(items)))
        return
    if name in {"p", "pre", "blockquote"}:
        text = node.get_text(" ", strip=True)
        if text:
            document.add(Element(type=ElementType.NARRATIVE, text=text))
        return
    for child in node.children:
        if isinstance(child, Tag):
            _walk(child, document)
