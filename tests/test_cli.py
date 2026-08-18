from __future__ import annotations

import json
from pathlib import Path

from preprocess_file.cli import main
from tests.fixtures import write_text


def test_cli_json(tmp_path: Path, capsys) -> None:
    path = write_text(tmp_path / "a.txt", "hello cli")
    assert main([str(path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["file_type"] == "txt"
    assert "hello cli" in payload["elements"][0]["text"]


def test_cli_markdown(tmp_path: Path, capsys) -> None:
    path = write_text(tmp_path / "a.md", "# Hello\n\nworld")
    assert main([str(path), "--md"]) == 0
    out = capsys.readouterr().out
    assert "# Hello" in out
    assert "world" in out
