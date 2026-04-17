from __future__ import annotations

from .draw.legend import draw_legend
from .draw.links import draw_transfer_connections
from .draw.lines import draw_lines
from .draw.stations import draw_stations
from .draw.title import draw_title_block
from .layout import get_pos_transform
from .markers import build_station_markers
from .segments import build_segment_index
from .styles import build_style_constants
from .utils import prepare_canvas


def draw_metro_map(
    data: dict,
    output_path: str,
    bg_path: str | None = None,
    font_paths: list[str] | None = None,
) -> None:
    from .router import build_line_polyline

    stations = data.get("stations", {})
    lines = data.get("lines", {})

    if not stations:
        return

    if font_paths is None:
        font_paths = []

    meta = data.get("meta", {})
    viewport = meta.get("viewport") if isinstance(meta, dict) else None

    layout = get_pos_transform(stations, viewport=viewport)
    scale_factor = layout.scale_factor
    width = layout.width
    height = layout.height
    get_pos = layout.get_pos

    img, draw = prepare_canvas(width, height, bg_path)

    styles = build_style_constants(scale_factor)
    line_width = float(styles["LINE_WIDTH"])

    segment_data = build_segment_index(lines, get_pos, build_line_polyline)
    line_polylines = segment_data.line_polylines
    line_meta = segment_data.line_meta
    skip_map = segment_data.skip_map
    segment_map = segment_data.segment_map
    segment_offsets = segment_data.segment_offsets
    line_segments_for_collision = segment_data.line_segments_for_collision

    station_markers = build_station_markers(lines)

    draw_lines(
        draw,
        line_polylines,
        line_meta,
        lines,
        segment_map,
        segment_offsets,
        styles,
        line_width,
    )

    draw_transfer_connections(
        draw,
        data.get("connections", []),
        get_pos,
        scale_factor,
        font_paths,
        styles,
    )

    draw_stations(
        img,
        draw,
        stations,
        lines,
        get_pos,
        skip_map,
        station_markers,
        line_segments_for_collision,
        scale_factor,
        font_paths,
        styles,
    )

    title_bottom = draw_title_block(draw, meta, font_paths, styles)

    draw_legend(
        draw,
        lines,
        font_paths,
        scale_factor,
        width,
        height,
        str(styles["COLOR_TEXT_MAIN"]),
        str(styles["COLOR_LEGEND_BORDER"]),
        title_bottom + 40 * scale_factor,
    )

    img.save(output_path)
    print(f"Saved to {output_path}")
