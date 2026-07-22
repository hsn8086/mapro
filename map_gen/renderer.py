from __future__ import annotations

from pathlib import Path

from PIL import Image

from .render_pipeline import draw_render_plan
from .render_plan import build_render_plan
from .svg_renderer import draw_metro_map_svg
from .utils import prepare_canvas


def draw_metro_map(
    data: dict,
    output_path: str,
    bg_path: str | None = None,
    font_paths: list[str] | None = None,
    *,
    badges_enabled: bool = True,
    preview_max_edge: int | None = None,
) -> None:
    stations = data.get("stations", {})

    if not stations:
        return

    if Path(output_path).suffix.lower() == ".svg":
        draw_metro_map_svg(
            data, output_path, bg_path, font_paths, badges_enabled=badges_enabled
        )
        return

    plan = build_render_plan(data, font_paths, badges_enabled=badges_enabled)
    layout = plan.layout
    width = layout.width
    height = layout.height

    img, draw = prepare_canvas(
        width, height, bg_path, bg_color=str(plan.styles.get("COLOR_BG", "#FAFAF7"))
    )
    draw_render_plan(plan, img, draw)

    if preview_max_edge is not None and max(img.size) > preview_max_edge:
        ratio = preview_max_edge / max(img.size)
        img = img.resize(
            (max(1, round(img.width * ratio)), max(1, round(img.height * ratio))),
            resample=Image.Resampling.LANCZOS,
        )

    img.save(output_path)
    print(f"Saved to {output_path}")
