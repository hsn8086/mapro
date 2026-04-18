from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .layout import Layout, get_pos_transform
from .markers import build_station_markers
from .router import build_line_polyline
from .segments import SegmentData, build_segment_index
from .stroke_builder import StrokeSegment, build_line_strokes
from .styles import build_style_constants


@dataclass(frozen=True)
class RenderPlan:
    layout: Layout
    styles: dict[str, float | str]
    stations: dict[str, Any]
    lines: dict[str, Any]
    meta: dict[str, Any]
    connections: list[dict[str, Any]]
    font_paths: list[str]
    segment_data: SegmentData
    station_markers: dict[str, list[dict[str, Any]]]
    line_width: float
    line_strokes: list[StrokeSegment]


def build_render_plan(
    data: dict[str, Any],
    font_paths: list[str] | None = None,
) -> RenderPlan:
    stations_raw = data.get("stations", {})
    lines_raw = data.get("lines", {})
    meta_raw = data.get("meta", {})
    connections_raw = data.get("connections", [])

    stations = stations_raw if isinstance(stations_raw, dict) else {}
    lines = lines_raw if isinstance(lines_raw, dict) else {}
    meta = meta_raw if isinstance(meta_raw, dict) else {}
    connections = (
        [item for item in connections_raw if isinstance(item, dict)]
        if isinstance(connections_raw, list)
        else []
    )

    resolved_font_paths = list(font_paths) if font_paths is not None else []
    viewport = meta.get("viewport") if isinstance(meta, dict) else None
    layout = get_pos_transform(stations, viewport=viewport)
    styles = build_style_constants(layout.scale_factor)
    segment_data = build_segment_index(lines, layout.get_pos, build_line_polyline)
    station_markers = build_station_markers(lines)
    line_width = float(styles["LINE_WIDTH"])
    line_strokes = build_line_strokes(
        segment_data.line_polylines,
        segment_data.line_meta,
        lines,
        segment_data.segment_map,
        segment_data.segment_offsets,
        styles,
        line_width,
    )

    return RenderPlan(
        layout=layout,
        styles=styles,
        stations=stations,
        lines=lines,
        meta=meta,
        connections=connections,
        font_paths=resolved_font_paths,
        segment_data=segment_data,
        station_markers=station_markers,
        line_width=line_width,
        line_strokes=line_strokes,
    )
