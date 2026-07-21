from __future__ import annotations

from pathlib import Path

from .render_pipeline import draw_render_plan
from .render_plan import build_render_plan
from .svg_renderer import draw_metro_map_svg
from .utils import prepare_canvas


def draw_metro_map(
    data: dict,
    output_path: str,
    bg_path: str | None = None,
    font_paths: list[str] | None = None,
) -> None:
    stations = data.get("stations", {})

    if not stations:
        return

    if Path(output_path).suffix.lower() == ".svg":
        draw_metro_map_svg(data, output_path, bg_path, font_paths)
        return

    plan = build_render_plan(data, font_paths)
    layout = plan.layout
    width = layout.width
    height = layout.height

    img, draw = prepare_canvas(width, height, bg_path)
    draw_render_plan(plan, img, draw)

    img.save(output_path)
    print(f"Saved to {output_path}")
