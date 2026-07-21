from __future__ import annotations

from dataclasses import dataclass
from math import acos, hypot, sin, tan

from .geometry import get_dir

Point = tuple[int, int]
FloatPoint = tuple[float, float]
NodeKind = str


@dataclass(frozen=True)
class PathNode:
    index: int
    point: Point
    kind: NodeKind
    dir_in: tuple[int, int]
    dir_out: tuple[int, int]
    is_turn: bool
    turn_signature: tuple[tuple[int, int], tuple[int, int]] | None


@dataclass(frozen=True)
class CornerCandidate:
    node_index: int
    point: Point
    dir_in: tuple[int, int]
    dir_out: tuple[int, int]
    segment_length_in: float
    segment_length_out: float
    turn_angle_radians: float
    max_radius: float


@dataclass(frozen=True)
class RoundedCornerGeometry:
    node_index: int
    corner_point: Point
    entry_point: FloatPoint
    exit_point: FloatPoint
    center_point: FloatPoint
    radius: float
    trim_distance: float
    clockwise: bool


def compress_collinear_points(points: list[Point]) -> list[Point]:
    if len(points) <= 2:
        return list(points)

    compressed: list[Point] = [points[0]]
    prev_dir = get_dir(points[0], points[1])

    for index in range(1, len(points) - 1):
        current = points[index]
        next_dir = get_dir(points[index], points[index + 1])
        if next_dir != prev_dir:
            compressed.append(current)
        prev_dir = next_dir

    compressed.append(points[-1])
    return compressed


def classify_path_nodes(points: list[Point]) -> tuple[PathNode, ...]:
    if not points:
        return ()

    nodes: list[PathNode] = []
    for index, point in enumerate(points):
        dir_in = (0, 0) if index == 0 else get_dir(points[index - 1], point)
        dir_out = (
            (0, 0) if index == len(points) - 1 else get_dir(point, points[index + 1])
        )

        if index == 0:
            kind: NodeKind = "start"
        elif index == len(points) - 1:
            kind = "end"
        elif dir_in != dir_out:
            kind = "corner"
        else:
            kind = "straight"

        is_turn = kind == "corner"
        turn_signature = (dir_in, dir_out) if is_turn else None
        nodes.append(
            PathNode(
                index=index,
                point=point,
                kind=kind,
                dir_in=dir_in,
                dir_out=dir_out,
                is_turn=is_turn,
                turn_signature=turn_signature,
            )
        )

    return tuple(nodes)


def _segment_length(p1: Point, p2: Point) -> float:
    return hypot(p2[0] - p1[0], p2[1] - p1[1])


def _normalize_vector(dx: float, dy: float) -> FloatPoint:
    length = hypot(dx, dy)
    if length == 0:
        return (0.0, 0.0)
    return (dx / length, dy / length)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _corner_angle(prev_point: Point, point: Point, next_point: Point) -> float:
    dir_to_prev = _normalize_vector(prev_point[0] - point[0], prev_point[1] - point[1])
    dir_to_next = _normalize_vector(next_point[0] - point[0], next_point[1] - point[1])
    dot = _clamp(
        dir_to_prev[0] * dir_to_next[0] + dir_to_prev[1] * dir_to_next[1],
        -1.0,
        1.0,
    )
    return acos(dot)


def _offset_point(point: Point, direction: FloatPoint, distance: float) -> FloatPoint:
    return (point[0] + direction[0] * distance, point[1] + direction[1] * distance)


def build_corner_candidates(
    points: list[Point],
    *,
    line_width: float,
) -> tuple[CornerCandidate, ...]:
    if len(points) < 3:
        return ()

    nodes = classify_path_nodes(points)
    candidates: list[CornerCandidate] = []
    base_radius = max(line_width * 0.75, 1.0)

    for node in nodes:
        if not node.is_turn or node.index == 0 or node.index == len(points) - 1:
            continue

        point_prev = points[node.index - 1]
        point_next = points[node.index + 1]
        segment_length_in = _segment_length(point_prev, node.point)
        segment_length_out = _segment_length(node.point, point_next)
        turn_angle_radians = _corner_angle(point_prev, node.point, point_next)
        if (
            turn_angle_radians <= 1e-6
            or abs(turn_angle_radians - 3.141592653589793) <= 1e-6
        ):
            continue

        limiting_length = min(segment_length_in, segment_length_out)
        length_limited_radius = (limiting_length * tan(turn_angle_radians / 2.0)) / 2.0
        max_radius = min(base_radius, length_limited_radius)
        if max_radius <= 0:
            continue

        candidates.append(
            CornerCandidate(
                node_index=node.index,
                point=node.point,
                dir_in=node.dir_in,
                dir_out=node.dir_out,
                segment_length_in=segment_length_in,
                segment_length_out=segment_length_out,
                turn_angle_radians=turn_angle_radians,
                max_radius=max_radius,
            )
        )

    return tuple(candidates)


def build_rounded_corner_geometry(
    points: list[Point],
    *,
    line_width: float,
) -> tuple[RoundedCornerGeometry, ...]:
    candidates = build_corner_candidates(points, line_width=line_width)
    geometries: list[RoundedCornerGeometry] = []

    for candidate in candidates:
        point_prev = points[candidate.node_index - 1]
        point_next = points[candidate.node_index + 1]
        dir_to_prev = _normalize_vector(
            point_prev[0] - candidate.point[0],
            point_prev[1] - candidate.point[1],
        )
        dir_to_next = _normalize_vector(
            point_next[0] - candidate.point[0],
            point_next[1] - candidate.point[1],
        )
        bisector = _normalize_vector(
            dir_to_prev[0] + dir_to_next[0],
            dir_to_prev[1] + dir_to_next[1],
        )
        if bisector == (0.0, 0.0):
            continue

        trim_distance = candidate.max_radius / tan(candidate.turn_angle_radians / 2.0)
        center_distance = candidate.max_radius / sin(candidate.turn_angle_radians / 2.0)
        entry_point = _offset_point(candidate.point, dir_to_prev, trim_distance)
        exit_point = _offset_point(candidate.point, dir_to_next, trim_distance)
        center_point = _offset_point(candidate.point, bisector, center_distance)

        travel_in = _normalize_vector(
            candidate.point[0] - point_prev[0],
            candidate.point[1] - point_prev[1],
        )
        travel_out = _normalize_vector(
            point_next[0] - candidate.point[0],
            point_next[1] - candidate.point[1],
        )
        cross = travel_in[0] * travel_out[1] - travel_in[1] * travel_out[0]

        geometries.append(
            RoundedCornerGeometry(
                node_index=candidate.node_index,
                corner_point=candidate.point,
                entry_point=entry_point,
                exit_point=exit_point,
                center_point=center_point,
                radius=candidate.max_radius,
                trim_distance=trim_distance,
                clockwise=cross < 0,
            )
        )

    return tuple(geometries)


def postprocess_polyline(points: list[Point]) -> list[Point]:
    return compress_collinear_points(points)
