from __future__ import annotations

from .draw.legend import draw_legend
from .draw.links import draw_transfer_connections
from .draw.lines import draw_lines
from .draw.stations import draw_stations
from .draw.title import draw_title_block
from .render_plan import build_render_plan
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

    plan = build_render_plan(data, font_paths)
    layout = plan.layout
    styles = plan.styles
    scale_factor = layout.scale_factor
    width = layout.width
    height = layout.height
    get_pos = layout.get_pos

    img, draw = prepare_canvas(width, height, bg_path)
    segment_data = plan.segment_data

    draw_lines(draw, plan.line_strokes)

    draw_transfer_connections(
        draw,
        plan.connections,
        get_pos,
        scale_factor,
        plan.font_paths,
        styles,
    )

    draw_stations(
        img,
        draw,
        plan.stations,
        plan.lines,
        get_pos,
        segment_data.skip_map,
        plan.station_markers,
        segment_data.line_segments_for_collision,
        segment_data.tram_line_segments_for_collision,
        scale_factor,
        plan.font_paths,
        styles,
    )

    draw_title_block(draw, plan.meta, plan.font_paths, styles)

    draw_legend(
        draw,
        plan.lines,
        plan.font_paths,
        scale_factor,
        width,
        height,
        str(styles["COLOR_TEXT_MAIN"]),
        str(styles["COLOR_LEGEND_BORDER"]),
        None,
    )

    img.save(output_path)
    print(f"Saved to {output_path}")
