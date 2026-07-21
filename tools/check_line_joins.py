from __future__ import annotations

from pathlib import Path
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from map_gen.draw.lines import draw_lines
from map_gen.stroke_builder import StrokeElement, StrokeSegment


def render_case(name: str, segments: list[StrokeElement]) -> None:
    image = Image.new("RGB", (320, 240), "white")
    draw = ImageDraw.Draw(image)
    draw_lines(draw, segments)
    output_dir = Path("debug")
    output_dir.mkdir(exist_ok=True)
    image.save(output_dir / f"{name}.png")


def main() -> None:
    render_case(
        "diag_to_horizontal",
        [
            StrokeSegment("1", (20.0, 220.0), (160.0, 80.0), "#cc004d", 20.0, False),
            StrokeSegment("1", (160.0, 80.0), (300.0, 80.0), "#cc004d", 20.0, False),
        ],
    )
    render_case(
        "horizontal_to_vertical",
        [
            StrokeSegment("1", (20.0, 120.0), (160.0, 120.0), "#0066cc", 20.0, False),
            StrokeSegment("1", (160.0, 120.0), (160.0, 40.0), "#0066cc", 20.0, False),
        ],
    )
    render_case(
        "diag_to_diag",
        [
            StrokeSegment("1", (20.0, 220.0), (160.0, 80.0), "#008844", 20.0, False),
            StrokeSegment("1", (160.0, 80.0), (280.0, 200.0), "#008844", 20.0, False),
        ],
    )


if __name__ == "__main__":
    main()
