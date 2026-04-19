from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .styles import is_non_active_status, resolve_status_color


@dataclass(frozen=True)
class StrokeSegment:
    line_id: str
    start: tuple[float, float]
    end: tuple[float, float]
    color: str
    thickness: float
    is_inactive: bool


def _resolve_base_color(
    line_data: dict[str, Any], styles: dict[str, float | str]
) -> tuple[str, str]:
    base_color = str(line_data.get("color", "#000000"))
    line_status = str(line_data.get("status", "active"))
    return (
        resolve_status_color(line_status, styles, active_color=base_color),
        line_status,
    )


def _build_point_map(line_meta: dict[str, Any]) -> dict[tuple[int, int], int]:
    points = line_meta.get("points", [])
    return {
        point: index for index, point in enumerate(points) if isinstance(point, tuple)
    }


def _resolve_segment_status(statuses: list[str], station_index: int) -> str:
    candidates: list[str] = []
    if station_index < len(statuses):
        candidates.append(statuses[station_index])
    if station_index + 1 < len(statuses):
        candidates.append(statuses[station_index + 1])

    for status in ("under_construction", "planned"):
        if status in candidates:
            return status
    return "active"


def _build_offset_segment(
    line_id: str,
    p1: tuple[int, int],
    p2: tuple[int, int],
    *,
    color: str,
    total_lines: int,
    line_index: int,
    line_width: float,
    is_tram: bool,
    is_inactive: bool,
) -> StrokeSegment | None:
    c_p1, c_p2 = (p2, p1) if p1 > p2 else (p1, p2)
    c_dx = c_p2[0] - c_p1[0]
    c_dy = c_p2[1] - c_p1[1]
    c_len = (c_dx * c_dx + c_dy * c_dy) ** 0.5
    if c_len == 0:
        return None

    c_ux = -c_dy / c_len
    c_uy = c_dx / c_len

    slot_width = line_width / total_lines
    draw_thickness = slot_width
    if is_tram and total_lines == 1:
        draw_thickness = slot_width * 0.5

    draw_thickness = max(1.5, draw_thickness)
    if abs(draw_thickness - slot_width) < 0.1:
        draw_thickness = int(draw_thickness + 1.5)

    offset_from_center = -line_width / 2.0 + slot_width * (line_index + 0.5)
    ox = c_ux * offset_from_center
    oy = c_uy * offset_from_center

    return StrokeSegment(
        line_id=line_id,
        start=(p1[0] + ox, p1[1] + oy),
        end=(p2[0] + ox, p2[1] + oy),
        color=color,
        thickness=draw_thickness,
        is_inactive=is_inactive,
    )


def build_line_strokes(
    line_polylines: dict[str, list[tuple[int, int]]],
    line_meta: dict[str, dict[str, Any]],
    lines: dict[str, Any],
    segment_map: dict[tuple[tuple[int, int], tuple[int, int]], list[str]],
    segment_offsets: dict[tuple[tuple[int, int], tuple[int, int]], dict[str, int]],
    styles: dict[str, float | str],
    line_width: float,
) -> list[StrokeSegment]:
    stroke_segments: list[StrokeSegment] = []

    for line_id, polyline in line_polylines.items():
        line_data_raw = lines.get(line_id, {})
        line_data = line_data_raw if isinstance(line_data_raw, dict) else {}
        meta = line_meta.get(line_id)
        if meta is None:
            continue

        point_map = _build_point_map(meta)
        statuses_raw = meta.get("statuses", [])
        statuses = [str(status) for status in statuses_raw]
        base_color, line_status = _resolve_base_color(line_data, styles)
        line_draw_state_station_idx = 0
        is_tram = str(line_data.get("type", "subway")) == "tram"

        for index in range(len(polyline) - 1):
            p1 = polyline[index]
            p2 = polyline[index + 1]

            if p1 in point_map:
                line_draw_state_station_idx = point_map[p1]

            segment_status = _resolve_segment_status(statuses, line_draw_state_station_idx)
            color = resolve_status_color(
                segment_status,
                styles,
                active_color=base_color,
            )
            is_inactive = is_non_active_status(line_status) or is_non_active_status(
                segment_status
            )

            key = (p2, p1) if p1 > p2 else (p1, p2)
            group = segment_map.get(key, [line_id])
            total_lines = len(group)
            line_index = segment_offsets.get(key, {}).get(line_id, 0)
            segment = _build_offset_segment(
                line_id,
                p1,
                p2,
                color=color,
                total_lines=total_lines,
                line_index=line_index,
                line_width=line_width,
                is_tram=is_tram,
                is_inactive=is_inactive,
            )
            if segment is not None:
                stroke_segments.append(segment)

    return stroke_segments
