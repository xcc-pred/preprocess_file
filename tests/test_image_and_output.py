from __future__ import annotations

from PIL import Image, ImageDraw

from preprocess_file.image_prep import deskew, estimate_skew_angle, preprocess_for_ocr
from preprocess_file.output import table_to_markdown


def test_table_to_markdown() -> None:
    markdown = table_to_markdown([["A", "B"], ["1", "2"]])
    assert markdown.splitlines()[0] == "| A | B |"
    assert "---" in markdown.splitlines()[1]


def test_deskew_reduces_rotation() -> None:
    image = Image.new("L", (400, 120), 255)
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 50, 380, 70), fill=0)
    rotated = image.rotate(8, fillcolor=255, expand=True)
    angle = estimate_skew_angle(rotated, max_angle=12)
    assert angle != 0
    corrected = deskew(rotated)
    assert corrected.size[0] > 0
    prepared = preprocess_for_ocr(rotated)
    assert prepared.mode == "L"
