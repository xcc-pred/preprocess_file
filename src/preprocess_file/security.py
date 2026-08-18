from __future__ import annotations

from pathlib import Path
import zipfile

from preprocess_file.errors import FileTooLargeError, RecursionLimitError, UnsafeArchiveError
from preprocess_file.models import ProcessContext, ProcessOptions


def assert_size(path: Path, options: ProcessOptions) -> None:
    size = path.stat().st_size
    if size > options.max_bytes:
        raise FileTooLargeError(
            f"{path} is {size} bytes, exceeding max_bytes={options.max_bytes}"
        )


def assert_depth(ctx: ProcessContext) -> None:
    if ctx.depth > ctx.options.max_recursion:
        raise RecursionLimitError(
            f"Recursion depth {ctx.depth} exceeds max_recursion={ctx.options.max_recursion}"
        )


def safe_zip_members(archive: zipfile.ZipFile, options: ProcessOptions) -> list[zipfile.ZipInfo]:
    infos = [info for info in archive.infolist() if not info.is_dir()]
    if len(infos) > options.max_zip_members:
        raise UnsafeArchiveError(
            f"Archive has {len(infos)} files, exceeding max_zip_members={options.max_zip_members}"
        )

    total = 0
    members: list[zipfile.ZipInfo] = []
    for info in infos:
        name = info.filename.replace("\\", "/")
        if name.startswith("/") or ".." in Path(name).parts:
            raise UnsafeArchiveError(f"Unsafe archive path: {info.filename}")
        total += max(info.file_size, 0)
        if total > options.max_zip_uncompressed:
            raise UnsafeArchiveError(
                f"Uncompressed size {total} exceeds max_zip_uncompressed={options.max_zip_uncompressed}"
            )
        members.append(info)
    return members


def is_junk_name(name: str) -> bool:
    lowered = name.replace("\\", "/").lower()
    base = Path(lowered).name
    return (
        lowered.startswith("__macosx/")
        or base in {".ds_store", "thumbs.db"}
        or base.startswith("~$")
    )
