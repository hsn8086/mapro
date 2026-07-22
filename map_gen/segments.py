from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from .geometry import get_dir

Point = tuple[int, int]
SegmentKey = tuple[Point, Point]


@dataclass(frozen=True)
class SharedSegment:
    key: SegmentKey
    start: Point
    end: Point
    line_ids: tuple[str, ...]
    is_shared: bool


@dataclass
class SegmentData:
    line_polylines: dict[str, list[Point]]
    line_meta: dict[str, dict]
    skip_map: set[tuple[str, str]]
    segment_map: dict[SegmentKey, list[str]]
    segment_offsets: dict[SegmentKey, dict[str, int]]
    line_segments_for_collision: list[SegmentKey]
    tram_line_segments_for_collision: list[SegmentKey]
    shared_segments: tuple[SharedSegment, ...]


def resolve_edge_shared_host(
    shared_hosts: list[str | None],
    station_index: int,
) -> str | None:
    """Host line for the edge leaving `station_index`, if both ends share it.

    An edge counts as shared track only when the line stations on both of
    its ends declare the same `sharedTrack` host.
    """
    if 0 <= station_index and station_index + 1 < len(shared_hosts):
        first = shared_hosts[station_index]
        second = shared_hosts[station_index + 1]
        if first is not None and first == second:
            return first
    return None


def _sort_bundle_line_ids(
    key: SegmentKey,
    line_ids: list[str],
    line_polylines: dict[str, list[Point]],
) -> list[str]:
    start, end = key

    def direction_before_after(line_id: str) -> tuple[tuple[int, int], tuple[int, int]]:
        polyline = line_polylines.get(line_id, [])
        for index in range(len(polyline) - 1):
            p1 = polyline[index]
            p2 = polyline[index + 1]
            normalized = (p2, p1) if p1 > p2 else (p1, p2)
            if normalized != key:
                continue

            before_dir = (0, 0)
            after_dir = (0, 0)
            if p1 == start and p2 == end:
                if index > 0:
                    before_dir = get_dir(polyline[index - 1], p1)
                if index + 2 < len(polyline):
                    after_dir = get_dir(p2, polyline[index + 2])
            else:
                if index > 0:
                    before_dir = get_dir(polyline[index - 1], p1)
                if index + 2 < len(polyline):
                    after_dir = get_dir(p2, polyline[index + 2])
                before_dir = (-before_dir[0], -before_dir[1])
                after_dir = (-after_dir[0], -after_dir[1])
            return (before_dir, after_dir)

        return ((0, 0), (0, 0))

    return sorted(
        line_ids, key=lambda line_id: (*direction_before_after(line_id), line_id)
    )


def build_segment_index(
    lines: dict,
    get_pos: Callable[[str], Point | None],
    build_line_polyline: Callable[[list[Point]], list[Point]],
) -> SegmentData:
    line_polylines: dict[str, list[Point]] = {}
    all_points: set[Point] = set()
    skip_map: set[tuple[str, str]] = set()
    line_meta: dict[str, dict] = {}

    for line_id, line in lines.items():
        line_stations = line.get("stations", [])
        pts: list[Point] = []
        statuses: list[str] = []
        shared_hosts: list[str | None] = []

        for s_item in line_stations:
            status = "active"
            shared_host: str | None = None
            if isinstance(s_item, dict):
                sid = s_item.get("id")
                s_status = s_item.get("status")
                if s_status:
                    status = s_status
                s_shared = s_item.get("sharedTrack")
                if s_shared:
                    shared_host = str(s_shared)

                if status in ["deferred", "pass"]:
                    skip_map.add((line_id, sid))
            else:
                sid = s_item

            pos = get_pos(sid)
            if pos:
                pts.append(pos)
                statuses.append(status)
                shared_hosts.append(shared_host)

        if len(pts) > 1:
            # LineStation status applies to the adjacent edge, so station
            # vertices must survive even when consecutive sections are straight.
            polyline = build_line_polyline(pts)
            line_polylines[line_id] = polyline
            line_meta[line_id] = {
                "points": pts,
                "statuses": statuses,
                "shared": shared_hosts,
            }
            for p in polyline:
                all_points.add(p)

    def is_on_segment(p: Point, a: Point, b: Point) -> bool:
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

    segment_map: dict[SegmentKey, list[str]] = defaultdict(list)
    for line_id, poly in line_polylines.items():
        if not poly:
            continue

        new_poly: list[Point] = []
        new_poly.append(poly[0])

        for i in range(len(poly) - 1):
            p_start = poly[i]
            p_end = poly[i + 1]

            on_segment: list[Point] = []
            for p in all_points:
                if is_on_segment(p, p_start, p_end):
                    on_segment.append(p)

            on_segment.sort(
                key=lambda p: (p[0] - p_start[0]) ** 2 + (p[1] - p_start[1]) ** 2
            )

            new_poly.extend(on_segment)
            new_poly.append(p_end)

        # keep injected collinear vertices: they align segment keys across
        # lines so shared runs can be detected; only drop exact duplicates
        deduped: list[Point] = []
        for point in new_poly:
            if not deduped or deduped[-1] != point:
                deduped.append(point)
        line_polylines[line_id] = deduped

        processed_poly = line_polylines[line_id]
        for i in range(len(processed_poly) - 1):
            p1 = processed_poly[i]
            p2 = processed_poly[i + 1]
            key = (p2, p1) if p1 > p2 else (p1, p2)
            segment_map[key].append(line_id)

    # shared-track edges ride on the host line: drop the guest from those
    # segments so bundling and station symbols see a single physical track
    for line_id, poly in line_polylines.items():
        meta = line_meta.get(line_id, {})
        shared_hosts = list(meta.get("shared", []))
        if not any(host is not None for host in shared_hosts):
            continue
        point_map = {point: index for index, point in enumerate(meta.get("points", []))}
        station_index = 0
        for i in range(len(poly) - 1):
            p1 = poly[i]
            p2 = poly[i + 1]
            if p1 in point_map:
                station_index = point_map[p1]
            host = resolve_edge_shared_host(shared_hosts, station_index)
            if host is None:
                continue
            key = (p2, p1) if p1 > p2 else (p1, p2)
            members = segment_map.get(key, [])
            if host in members and line_id in members:
                members.remove(line_id)

    segment_offsets: dict[SegmentKey, dict[str, int]] = {}
    shared_segments: list[SharedSegment] = []
    for key, line_ids in segment_map.items():
        ordered_line_ids = _sort_bundle_line_ids(key, list(line_ids), line_polylines)
        offsets = {lid: i for i, lid in enumerate(ordered_line_ids)}
        segment_offsets[key] = offsets
        shared_segments.append(
            SharedSegment(
                key=key,
                start=key[0],
                end=key[1],
                line_ids=tuple(ordered_line_ids),
                is_shared=len(ordered_line_ids) > 1,
            )
        )

    line_segments_for_collision: list[SegmentKey] = []
    tram_line_segments_for_collision: list[SegmentKey] = []
    for shared_segment in shared_segments:
        line_segments_for_collision.append(shared_segment.key)
        if any(
            str(lines.get(line_id, {}).get("type", "subway")) == "tram"
            for line_id in shared_segment.line_ids
        ):
            tram_line_segments_for_collision.append(shared_segment.key)

    shared_segments.sort(
        key=lambda segment: (segment.start, segment.end, segment.line_ids)
    )

    return SegmentData(
        line_polylines=line_polylines,
        line_meta=line_meta,
        skip_map=skip_map,
        segment_map=segment_map,
        segment_offsets=segment_offsets,
        line_segments_for_collision=line_segments_for_collision,
        tram_line_segments_for_collision=tram_line_segments_for_collision,
        shared_segments=tuple(shared_segments),
    )
