from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable


@dataclass
class SegmentData:
    line_polylines: dict[str, list[tuple[int, int]]]
    line_meta: dict[str, dict]
    skip_map: set[tuple[str, str]]
    segment_map: dict[tuple[tuple[int, int], tuple[int, int]], list[str]]
    segment_offsets: dict[tuple[tuple[int, int], tuple[int, int]], dict[str, int]]
    line_segments_for_collision: list[tuple[tuple[int, int], tuple[int, int]]]


def build_segment_index(
    lines: dict,
    get_pos: Callable[[str], tuple[int, int] | None],
    build_line_polyline: Callable[[list[tuple[int, int]]], list[tuple[int, int]]],
) -> SegmentData:
    line_polylines: dict[str, list[tuple[int, int]]] = {}
    all_points: set[tuple[int, int]] = set()
    skip_map: set[tuple[str, str]] = set()
    line_meta: dict[str, dict] = {}

    for line_id, line in lines.items():
        line_stations = line.get("stations", [])
        pts: list[tuple[int, int]] = []
        statuses: list[str] = []

        for s_item in line_stations:
            status = "active"
            if isinstance(s_item, dict):
                sid = s_item.get("id")
                s_status = s_item.get("status")
                if s_status:
                    status = s_status

                if status in ["deferred", "pass"]:
                    skip_map.add((line_id, sid))
            else:
                sid = s_item

            pos = get_pos(sid)
            if pos:
                pts.append(pos)
                statuses.append(status)

        if len(pts) > 1:
            polyline = build_line_polyline(pts)
            line_polylines[line_id] = polyline
            line_meta[line_id] = {"points": pts, "statuses": statuses}
            for p in polyline:
                all_points.add(p)

    def is_on_segment(
        p: tuple[int, int], a: tuple[int, int], b: tuple[int, int]
    ) -> bool:
        if p == a or p == b:
            return False
        dx1, dy1 = b[0] - a[0], b[1] - a[1]
        dx2, dy2 = p[0] - a[0], p[1] - a[1]
        cross = dx1 * dy2 - dx2 * dy1
        if abs(cross) > 1e-9:
            return False

        dot = dx1 * dx2 + dy1 * dy2
        if dot < 0:
            return False
        squared_len = dx1 * dx1 + dy1 * dy1
        if dot > squared_len:
            return False
        return True

    segment_map: dict[tuple[tuple[int, int], tuple[int, int]], list[str]] = defaultdict(
        list
    )
    for line_id, poly in line_polylines.items():
        if not poly:
            continue

        new_poly: list[tuple[int, int]] = []
        new_poly.append(poly[0])

        for i in range(len(poly) - 1):
            p_start = poly[i]
            p_end = poly[i + 1]

            on_segment: list[tuple[int, int]] = []
            for p in all_points:
                if is_on_segment(p, p_start, p_end):
                    on_segment.append(p)

            on_segment.sort(
                key=lambda p: (p[0] - p_start[0]) ** 2 + (p[1] - p_start[1]) ** 2
            )

            new_poly.extend(on_segment)
            new_poly.append(p_end)

        line_polylines[line_id] = new_poly

        for i in range(len(new_poly) - 1):
            p1 = new_poly[i]
            p2 = new_poly[i + 1]
            key = (p2, p1) if p1 > p2 else (p1, p2)
            segment_map[key].append(line_id)

    segment_offsets: dict[tuple[tuple[int, int], tuple[int, int]], dict[str, int]] = {}
    for key, line_ids in segment_map.items():
        line_ids.sort()
        offsets = {lid: i for i, lid in enumerate(line_ids)}
        segment_offsets[key] = offsets

    line_segments_for_collision: list[tuple[tuple[int, int], tuple[int, int]]] = []
    unique_segments = set(segment_map.keys())
    for s in unique_segments:
        line_segments_for_collision.append(s)

    return SegmentData(
        line_polylines=line_polylines,
        line_meta=line_meta,
        skip_map=skip_map,
        segment_map=segment_map,
        segment_offsets=segment_offsets,
        line_segments_for_collision=line_segments_for_collision,
    )
