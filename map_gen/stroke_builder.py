from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .segments import resolve_edge_shared_host
from .styles import is_non_active_status, resolve_status_color

Point = tuple[int, int]
FloatPoint = tuple[float, float]
SegmentKey = tuple[Point, Point]


@dataclass(frozen=True)
class StrokeSegment:
    line_id: str
    start: FloatPoint
    end: FloatPoint
    color: str
    thickness: float
    is_inactive: bool


@dataclass(frozen=True)
class StrokeArc:
    line_id: str
    center: FloatPoint
    radius: float
    start_angle: float
    end_angle: float
    clockwise: bool
    color: str
    thickness: float
    is_inactive: bool

    @property
    def start(self) -> FloatPoint:
        return (
            self.center[0] + math.cos(self.start_angle) * self.radius,
            self.center[1] + math.sin(self.start_angle) * self.radius,
        )

    @property
    def end(self) -> FloatPoint:
        return (
            self.center[0] + math.cos(self.end_angle) * self.radius,
            self.center[1] + math.sin(self.end_angle) * self.radius,
        )


StrokeElement = StrokeSegment | StrokeArc


def _resolve_base_color(
    line_data: dict[str, Any], styles: dict[str, float | str]
) -> tuple[str, str]:
    base_color = str(line_data.get("color", "#000000"))
    line_status = str(line_data.get("status", "active"))
    return (
        resolve_status_color(line_status, styles, active_color=base_color),
        line_status,
    )


def _build_point_map(line_meta: dict[str, Any]) -> dict[Point, int]:
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


def _canonical_key(p1: Point, p2: Point) -> SegmentKey:
    return (p2, p1) if p1 > p2 else (p1, p2)


def _normalize(dx: float, dy: float) -> FloatPoint:
    length = math.hypot(dx, dy)
    if length == 0:
        return (0.0, 0.0)
    return (dx / length, dy / length)


def _canonical_left_normal(key: SegmentKey) -> FloatPoint:
    direction = _normalize(key[1][0] - key[0][0], key[1][1] - key[0][1])
    return (-direction[1], direction[0])


def _line_intersection(
    p: FloatPoint, d1: FloatPoint, q: FloatPoint, d2: FloatPoint
) -> FloatPoint | None:
    denominator = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(denominator) < 1e-9:
        return None
    t = ((q[0] - p[0]) * d2[1] - (q[1] - p[1]) * d2[0]) / denominator
    return (p[0] + d1[0] * t, p[1] + d1[1] * t)


def _foot_of_perpendicular(
    center: FloatPoint, origin: FloatPoint, direction: FloatPoint
) -> FloatPoint:
    t = (center[0] - origin[0]) * direction[0] + (center[1] - origin[1]) * direction[1]
    return (origin[0] + direction[0] * t, origin[1] + direction[1] * t)


@dataclass
class _OffsetSegment:
    start: FloatPoint
    end: FloatPoint
    direction: FloatPoint
    color: str
    is_inactive: bool
    center_start: Point
    center_end: Point
    lateral: float


def _corner_arc(
    line_id: str,
    center: FloatPoint,
    entry: FloatPoint,
    exit_: FloatPoint,
    clockwise: bool,
    color: str,
    thickness: float,
    is_inactive: bool,
) -> StrokeArc | None:
    radius = math.hypot(entry[0] - center[0], entry[1] - center[1])
    if radius < 0.5:
        return None
    start_angle = math.atan2(entry[1] - center[1], entry[0] - center[0])
    end_angle = math.atan2(exit_[1] - center[1], exit_[0] - center[0])
    return StrokeArc(
        line_id=line_id,
        center=center,
        radius=radius,
        start_angle=start_angle,
        end_angle=end_angle,
        clockwise=clockwise,
        color=color,
        thickness=thickness,
        is_inactive=is_inactive,
    )


def _build_line_elements(
    line_id: str,
    segments: list[_OffsetSegment],
    *,
    corner_radius: float,
    thickness: float,
) -> list[StrokeElement]:
    """Join offset segments with miters and replace corners with true arcs."""
    if not segments:
        return []

    count = len(segments)
    starts = [seg.start for seg in segments]
    ends = [seg.end for seg in segments]
    arcs: list[StrokeArc | None] = [None] * count
    ramps: list[StrokeSegment | None] = [None] * count

    for index in range(count - 1):
        seg_a = segments[index]
        seg_b = segments[index + 1]
        cross = (
            seg_a.direction[0] * seg_b.direction[1]
            - seg_a.direction[1] * seg_b.direction[0]
        )
        if abs(cross) < 1e-9:
            # parallel: continuous run, or a lateral jog at a bundle
            # boundary that must be absorbed by a 45-degree ramp
            forward = (
                seg_a.direction[0] * seg_b.direction[0]
                + seg_a.direction[1] * seg_b.direction[1]
            )
            gap = math.hypot(
                seg_b.start[0] - seg_a.end[0], seg_b.start[1] - seg_a.end[1]
            )
            if forward <= 0 or gap <= 1e-6:
                continue
            direction = seg_a.direction
            length_a = math.hypot(
                seg_a.end[0] - seg_a.start[0], seg_a.end[1] - seg_a.start[1]
            )
            length_b = math.hypot(
                seg_b.end[0] - seg_b.start[0], seg_b.end[1] - seg_b.start[1]
            )
            if abs(seg_a.lateral) <= abs(seg_b.lateral):
                # ramp before entering the offset run
                run = min(gap, length_a * 0.5)
                ends[index] = (
                    seg_a.end[0] - direction[0] * run,
                    seg_a.end[1] - direction[1] * run,
                )
                ramp_start, ramp_end = ends[index], starts[index + 1]
            else:
                # ramp after leaving the offset run
                run = min(gap, length_b * 0.5)
                starts[index + 1] = (
                    seg_b.start[0] + direction[0] * run,
                    seg_b.start[1] + direction[1] * run,
                )
                ramp_start, ramp_end = ends[index], starts[index + 1]
            ramps[index] = StrokeSegment(
                line_id=line_id,
                start=ramp_start,
                end=ramp_end,
                color=seg_b.color,
                thickness=thickness,
                is_inactive=seg_b.is_inactive,
            )
            continue

        dir_to_prev = (-seg_a.direction[0], -seg_a.direction[1])
        dir_to_next = seg_b.direction
        dot = max(
            -1.0,
            min(
                1.0,
                dir_to_prev[0] * dir_to_next[0] + dir_to_prev[1] * dir_to_next[1],
            ),
        )
        turn_angle = math.acos(dot)
        if turn_angle <= 1e-6 or abs(turn_angle - math.pi) <= 1e-6:
            continue

        bisector = _normalize(
            dir_to_prev[0] + dir_to_next[0], dir_to_prev[1] + dir_to_next[1]
        )
        if bisector == (0.0, 0.0):
            continue

        miter = _line_intersection(
            seg_a.start, seg_a.direction, seg_b.start, seg_b.direction
        )
        if miter is None:
            continue

        # canonical scalars flip sign across corners while the geometric
        # side stays put, so compare magnitudes only
        in_bundle_corner = (
            seg_a.center_end == seg_b.center_start
            and abs(abs(seg_a.lateral) - abs(seg_b.lateral)) < 1e-9
            and abs(seg_a.lateral) > 1e-9
        )

        if in_bundle_corner:
            # concentric: fillet computed on the shared centreline, then the
            # arc for this stroke is the projection onto its offset lines,
            # so every member of the bundle shares the same centre point
            vertex = seg_a.center_end
            length_in = math.hypot(
                vertex[0] - seg_a.center_start[0], vertex[1] - seg_a.center_start[1]
            )
            length_out = math.hypot(
                seg_b.center_end[0] - vertex[0], seg_b.center_end[1] - vertex[1]
            )
            limit = min(length_in, length_out) * 0.45 * math.tan(turn_angle / 2.0)
            radius = min(corner_radius, limit)
            if radius <= 0.5:
                ends[index] = miter
                starts[index + 1] = miter
                continue
            center_distance = radius / math.sin(turn_angle / 2.0)
            center = (
                vertex[0] + bisector[0] * center_distance,
                vertex[1] + bisector[1] * center_distance,
            )
            entry = _foot_of_perpendicular(center, seg_a.start, seg_a.direction)
            exit_ = _foot_of_perpendicular(center, seg_b.start, seg_b.direction)
            arc = _corner_arc(
                line_id,
                center,
                entry,
                exit_,
                cross < 0,
                seg_b.color,
                thickness,
                seg_b.is_inactive,
            )
            if arc is None:
                ends[index] = miter
                starts[index + 1] = miter
                continue
            ends[index] = entry
            starts[index + 1] = exit_
            arcs[index] = arc
            continue

        length_a = math.hypot(miter[0] - seg_a.start[0], miter[1] - seg_a.start[1])
        length_b = math.hypot(seg_b.end[0] - miter[0], seg_b.end[1] - miter[1])
        limit = min(length_a, length_b) * 0.45 * math.tan(turn_angle / 2.0)
        radius = min(corner_radius, limit)
        if radius <= 0.5:
            ends[index] = miter
            starts[index + 1] = miter
            continue

        trim = radius / math.tan(turn_angle / 2.0)
        center_distance = radius / math.sin(turn_angle / 2.0)
        center = (
            miter[0] + bisector[0] * center_distance,
            miter[1] + bisector[1] * center_distance,
        )
        entry = (
            miter[0] + dir_to_prev[0] * trim,
            miter[1] + dir_to_prev[1] * trim,
        )
        exit_ = (
            miter[0] + dir_to_next[0] * trim,
            miter[1] + dir_to_next[1] * trim,
        )
        ends[index] = entry
        starts[index + 1] = exit_
        arcs[index] = _corner_arc(
            line_id,
            center,
            entry,
            exit_,
            cross < 0,
            seg_b.color,
            thickness,
            seg_b.is_inactive,
        )

    elements: list[StrokeElement] = []
    for index in range(count):
        seg = segments[index]
        start = starts[index]
        end = ends[index]
        if math.hypot(end[0] - start[0], end[1] - start[1]) > 1e-6:
            elements.append(
                StrokeSegment(
                    line_id=line_id,
                    start=start,
                    end=end,
                    color=seg.color,
                    thickness=thickness,
                    is_inactive=seg.is_inactive,
                )
            )
        arc = arcs[index]
        if arc is not None:
            elements.append(arc)
        ramp = ramps[index]
        if ramp is not None:
            elements.append(ramp)
    return elements


def build_active_segment_keys(
    line_polylines: dict[str, list[Point]],
    line_meta: dict[str, dict[str, Any]],
    lines: dict[str, Any],
) -> set[SegmentKey]:
    """Segment keys carried by at least one in-service line portion.

    Segments only served by planned / under-construction strokes are not
    included, so label placement can treat them as soft obstacles.
    """
    active: set[SegmentKey] = set()

    for line_id, polyline in line_polylines.items():
        line_data_raw = lines.get(line_id, {})
        line_data = line_data_raw if isinstance(line_data_raw, dict) else {}
        if is_non_active_status(str(line_data.get("status", "active"))):
            continue
        meta = line_meta.get(line_id)
        if meta is None:
            continue
        point_map = _build_point_map(meta)
        statuses = [str(status) for status in meta.get("statuses", [])]
        shared_hosts = [
            host if isinstance(host, str) else None for host in meta.get("shared", [])
        ]
        station_index = 0
        for index in range(len(polyline) - 1):
            p1 = polyline[index]
            p2 = polyline[index + 1]
            if p1 in point_map:
                station_index = point_map[p1]
            # shared-track edges belong to the host line's stroke
            if resolve_edge_shared_host(shared_hosts, station_index) is not None:
                continue
            segment_status = _resolve_segment_status(statuses, station_index)
            if not is_non_active_status(segment_status):
                active.add(_canonical_key(p1, p2))

    return active


def build_line_strokes(
    line_polylines: dict[str, list[Point]],
    line_meta: dict[str, dict[str, Any]],
    lines: dict[str, Any],
    segment_map: dict[SegmentKey, list[str]],
    bundle_offsets: dict[tuple[str, SegmentKey], float],
    styles: dict[str, float | str],
    line_width: float,
) -> list[StrokeElement]:
    corner_radius = float(styles.get("CORNER_RADIUS", line_width * 1.25))
    stroke_elements: list[StrokeElement] = []

    for line_id, polyline in line_polylines.items():
        line_data_raw = lines.get(line_id, {})
        line_data = line_data_raw if isinstance(line_data_raw, dict) else {}
        meta = line_meta.get(line_id)
        if meta is None:
            continue

        point_map = _build_point_map(meta)
        statuses = [str(status) for status in meta.get("statuses", [])]
        shared_hosts = [
            host if isinstance(host, str) else None for host in meta.get("shared", [])
        ]
        base_color, line_status = _resolve_base_color(line_data, styles)
        is_tram = str(line_data.get("type", "subway")) == "tram"
        thickness = line_width * (0.55 if is_tram else 1.0)
        station_index = 0

        # shared-track edges are drawn by the host line only; split the
        # remaining edges into contiguous runs so miters and corner arcs
        # never join across a skipped stretch
        segment_runs: list[list[_OffsetSegment]] = [[]]
        for index in range(len(polyline) - 1):
            p1 = polyline[index]
            p2 = polyline[index + 1]
            if p1 in point_map:
                station_index = point_map[p1]

            if resolve_edge_shared_host(shared_hosts, station_index) is not None:
                if segment_runs[-1]:
                    segment_runs.append([])
                continue

            segment_status = _resolve_segment_status(statuses, station_index)
            color = resolve_status_color(
                segment_status, styles, active_color=base_color
            )
            is_inactive = is_non_active_status(line_status) or is_non_active_status(
                segment_status
            )

            key = _canonical_key(p1, p2)
            lateral = bundle_offsets.get((line_id, key), 0.0)
            normal = _canonical_left_normal(key)
            offset_vec = (normal[0] * lateral, normal[1] * lateral)
            direction = _normalize(p2[0] - p1[0], p2[1] - p1[1])
            if direction == (0.0, 0.0):
                continue
            segment_runs[-1].append(
                _OffsetSegment(
                    start=(p1[0] + offset_vec[0], p1[1] + offset_vec[1]),
                    end=(p2[0] + offset_vec[0], p2[1] + offset_vec[1]),
                    direction=direction,
                    color=color,
                    is_inactive=is_inactive,
                    center_start=p1,
                    center_end=p2,
                    lateral=lateral,
                )
            )

        for run in segment_runs:
            stroke_elements.extend(
                _build_line_elements(
                    line_id,
                    run,
                    corner_radius=corner_radius,
                    thickness=thickness,
                )
            )

    return stroke_elements
