from __future__ import annotations

from pathlib import Path
import tempfile
import zipfile
import xml.etree.ElementTree as ET

from preprocess_file.errors import UnsafeArchiveError
from preprocess_file.handlers.base import Handler
from preprocess_file.models import Document, FileKind, ProcessContext
from preprocess_file.security import assert_depth, is_junk_name, safe_zip_members


class ArchiveHandler(Handler):
    kinds = (FileKind.ZIP, FileKind.EPUB)

    def process(self, ctx: ProcessContext) -> Document:
        kind = ctx.kind or FileKind.ZIP
        document = Document(source=str(ctx.path), file_type=kind)
        if ctx.pipeline is None:
            document.warnings.append("Archive handler requires the pipeline for recursive processing.")
            return document
        assert_depth(ctx)

        with zipfile.ZipFile(ctx.path) as archive:
            members = [
                info
                for info in safe_zip_members(archive, ctx.options)
                if not is_junk_name(info.filename)
            ]
            document.metadata["members"] = [info.filename for info in members]
            ordered = _epub_reading_order(archive, members) if kind is FileKind.EPUB else members
            with tempfile.TemporaryDirectory(prefix="preprocess-zip-") as tmp:
                root = Path(tmp)
                for info in ordered:
                    extracted = _safe_extract(archive, info, root)
                    if extracted is None:
                        continue
                    child_ctx = ProcessContext(
                        path=extracted,
                        options=ctx.options,
                        depth=ctx.depth + 1,
                        pipeline=ctx.pipeline,
                    )
                    try:
                        assert_depth(child_ctx)
                        child = ctx.pipeline.process_context(child_ctx)
                        document.extend(child, prefix=info.filename)
                    except Exception as exc:
                        document.warnings.append(f"Failed to process {info.filename}: {exc}")
        return document


def _safe_extract(archive: zipfile.ZipFile, info: zipfile.ZipInfo, root: Path) -> Path | None:
    name = info.filename.replace("\\", "/")
    target = (root / name).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise UnsafeArchiveError(f"Refusing to extract {info.filename}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with archive.open(info) as source, target.open("wb") as dest:
        dest.write(source.read())
    return target


def _epub_reading_order(archive: zipfile.ZipFile, members: list[zipfile.ZipInfo]) -> list[zipfile.ZipInfo]:
    by_name = {info.filename.replace("\\", "/"): info for info in members}
    try:
        container = ET.fromstring(archive.read("META-INF/container.xml"))
        rootfile = container.find(".//{*}rootfile")
        if rootfile is None:
            return members
        opf_path = rootfile.attrib.get("full-path")
        if not opf_path:
            return members
        opf = ET.fromstring(archive.read(opf_path))
        manifest = {
            item.attrib["id"]: item.attrib.get("href", "")
            for item in opf.findall(".//{*}item")
            if "id" in item.attrib
        }
        spine_hrefs = [manifest.get(item.attrib.get("idref", ""), "") for item in opf.findall(".//{*}itemref")]
        base = str(Path(opf_path).parent).replace("\\", "/")
        ordered: list[zipfile.ZipInfo] = []
        seen: set[str] = set()
        for href in spine_hrefs:
            if not href:
                continue
            joined = href if base in {".", ""} else f"{base}/{href}"
            joined = joined.replace("\\", "/")
            if joined in by_name and joined not in seen:
                ordered.append(by_name[joined])
                seen.add(joined)
        for info in members:
            key = info.filename.replace("\\", "/")
            if key not in seen:
                ordered.append(info)
        return ordered
    except Exception:
        return members
