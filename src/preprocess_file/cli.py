from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from preprocess_file.errors import PreprocessError
from preprocess_file.models import ProcessOptions
from preprocess_file.pipeline import process


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="preprocess-file",
        description="Preprocess a file into structured JSON / Markdown.",
    )
    parser.add_argument("path", type=Path, help="Input file")
    parser.add_argument("--json", action="store_true", help="Print JSON (default if --md is absent)")
    parser.add_argument("--md", action="store_true", help="Print Markdown")
    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR for scans and images")
    parser.add_argument("--max-bytes", type=int, default=100 * 1024 * 1024)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    options = ProcessOptions(max_bytes=args.max_bytes, ocr_enabled=not args.no_ocr)
    try:
        document = process(args.path, options)
    except PreprocessError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except FileNotFoundError:
        print(f"File not found: {args.path}", file=sys.stderr)
        return 2

    if args.md and not args.json:
        print(document.to_markdown())
        return 0
    payload = document.to_dict()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.md:
        print("\n--- markdown ---\n")
        print(document.to_markdown())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
