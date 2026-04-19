from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal, Sequence

Point = tuple[int, int]
Direction = tuple[int, int]
CorridorAxis = Literal["none", "horizontal", "vertical", "diag_pos", "diag_neg"]

DEFAULT_DIRECTIONS: tuple[Direction, ...] = (
    (1, 0),
    (1, 1),
    (1, -1),
    (0, -1),
    (0, 1),
    (-1, -1),
    (-1, 0),
    (-1, 1),
)


@dataclass(frozen=True)
class StationContextInput:
    station_id: str
    pos: Point
    block_width: float
    block_height: float
    is_transfer: bool
    has_badges: bool
    name_length: int


@dataclass(frozen=True)
class NearbyStation:
    station_id: str
    pos: Point
    is_transfer: bool
    block_width: float
    block_height: float
    has_badges: bool
    name_length: int


@dataclass(frozen=True)
class LocalLabelContext:
    station_id: str
    dense: bool
    cluster_id: int | None
    corridor_axis: CorridorAxis
    corridor_index: int
    preferred_directions: tuple[Direction, ...]
    tangent_vector: tuple[float, float]
    nearby_stations: tuple[NearbyStation, ...]


def _distance(p1: Point, p2: Point) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def _normalize(vector: tuple[float, float]) -> tuple[float, float]:
    length = math.hypot(vector[0], vector[1])
    if length == 0:
        return (0.0, 0.0)
    return (vector[0] / length, vector[1] / length)


def _build_neighbors(
    inputs: Sequence[StationContextInput], radius: float
) -> dict[str, list[str]]:
    neighbors: dict[str, list[str]] = {item.station_id: [] for item in inputs}
    for index, item in enumerate(inputs):
        for other in inputs[index + 1 :]:
            if _distance(item.pos, other.pos) <= radius:
                neighbors[item.station_id].append(other.station_id)
                neighbors[other.station_id].append(item.station_id)
    return neighbors


def _build_components(neighbors: dict[str, list[str]]) -> list[list[str]]:
    seen: set[str] = set()
    components: list[list[str]] = []
    for station_id in neighbors:
        if station_id in seen:
            continue
        stack = [station_id]
        component: list[str] = []
        seen.add(station_id)
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in neighbors[current]:
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                stack.append(neighbor)
        components.append(component)
    return components


def _resolve_corridor_axis(points: Sequence[Point]) -> CorridorAxis:
    if len(points) < 2:
        return "none"

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)
    if span_x > span_y * 1.6:
        return "horizontal"
    if span_y > span_x * 1.6:
        return "vertical"

    farthest_pair: tuple[Point, Point] | None = None
    farthest_distance = -1.0
    for index, point in enumerate(points):
        for other in points[index + 1 :]:
            distance = _distance(point, other)
            if distance > farthest_distance:
                farthest_distance = distance
                farthest_pair = (point, other)

    if farthest_pair is None:
        return "none"

    dx = farthest_pair[1][0] - farthest_pair[0][0]
    dy = farthest_pair[1][1] - farthest_pair[0][1]
    return "diag_pos" if dx * dy >= 0 else "diag_neg"


def _sort_key(axis: CorridorAxis, item: StationContextInput) -> float:
    if axis == "horizontal":
        return float(item.pos[0])
    if axis == "vertical":
        return float(item.pos[1])
    if axis == "diag_pos":
        return float(item.pos[0] + item.pos[1])
    if axis == "diag_neg":
        return float(item.pos[0] - item.pos[1])
    return float(item.name_length)


def _dense_priority(
    item: StationContextInput, axis: CorridorAxis
) -> tuple[float, float, float]:
    major = 0.0 if item.is_transfer else 1.0
    medium = -float(max(item.block_width, item.block_height))
    fallback = _sort_key(axis, item)
    return (major, medium, fallback)


def _preferred_directions(axis: CorridorAxis, index: int) -> tuple[Direction, ...]:
    if axis == "vertical":
        return (
            ((1, 0), (1, 1), (1, -1), (0, -1), (0, 1), (-1, 0), (-1, -1), (-1, 1))
            if index % 2 == 0
            else ((-1, 0), (-1, -1), (-1, 1), (0, -1), (0, 1), (1, 0), (1, 1), (1, -1))
        )
    if axis == "horizontal":
        return (
            ((0, -1), (0, 1), (1, -1), (-1, -1), (1, 0), (-1, 0), (1, 1), (-1, 1))
            if index % 2 == 0
            else ((0, 1), (0, -1), (1, 1), (-1, 1), (1, 0), (-1, 0), (1, -1), (-1, -1))
        )
    if axis == "diag_pos":
        return (
            ((1, -1), (1, 0), (0, -1), (1, 1), (-1, -1), (0, 1), (-1, 0), (-1, 1))
            if index % 2 == 0
            else ((-1, 1), (-1, 0), (0, 1), (-1, -1), (1, 1), (0, -1), (1, 0), (1, -1))
        )
    if axis == "diag_neg":
        return (
            ((1, 1), (1, 0), (0, -1), (1, -1), (-1, 1), (0, 1), (-1, 0), (-1, -1))
            if index % 2 == 0
            else ((-1, -1), (-1, 0), (0, 1), (-1, 1), (1, -1), (0, -1), (1, 0), (1, 1))
        )
    return DEFAULT_DIRECTIONS


def _tangent_vector(axis: CorridorAxis) -> tuple[float, float]:
    if axis == "horizontal":
        return (1.0, 0.0)
    if axis == "vertical":
        return (0.0, 1.0)
    if axis == "diag_pos":
        return _normalize((1.0, 1.0))
    if axis == "diag_neg":
        return _normalize((1.0, -1.0))
    return (0.0, 0.0)


def build_local_label_contexts(
    inputs: Sequence[StationContextInput],
    scale_factor: int,
) -> dict[str, LocalLabelContext]:
    if not inputs:
        return {}

    radius = 70.0 * scale_factor
    neighbors = _build_neighbors(inputs, radius)
    tight_pair_radius = 75.0 * scale_factor
    for index, item in enumerate(inputs):
        for other in inputs[index + 1 :]:
            if _distance(item.pos, other.pos) > tight_pair_radius:
                continue
            if item.station_id in neighbors[other.station_id]:
                continue
            neighbors[item.station_id].append(other.station_id)
            neighbors[other.station_id].append(item.station_id)
    components = _build_components(neighbors)
    input_map = {item.station_id: item for item in inputs}
    contexts: dict[str, LocalLabelContext] = {}

    cluster_counter = 0
    for component in components:
        dense = len(component) >= 3
        if not dense and len(component) == 2:
            first = input_map[component[0]]
            second = input_map[component[1]]
            if _distance(first.pos, second.pos) <= tight_pair_radius:
                dense = True
        axis: CorridorAxis = "none"
        ordered_ids = list(component)
        cluster_id: int | None = None
        if dense:
            cluster_id = cluster_counter
            cluster_counter += 1
            points = [input_map[station_id].pos for station_id in component]
            axis = _resolve_corridor_axis(points)
            ordered_ids = sorted(
                component,
                key=lambda station_id: _dense_priority(input_map[station_id], axis),
            )

        order_index = {
            station_id: index for index, station_id in enumerate(ordered_ids)
        }

        for station_id in component:
            item = input_map[station_id]
            nearby = tuple(
                NearbyStation(
                    station_id=neighbor_id,
                    pos=input_map[neighbor_id].pos,
                    is_transfer=input_map[neighbor_id].is_transfer,
                    block_width=input_map[neighbor_id].block_width,
                    block_height=input_map[neighbor_id].block_height,
                    has_badges=input_map[neighbor_id].has_badges,
                    name_length=input_map[neighbor_id].name_length,
                )
                for neighbor_id in sorted(
                    neighbors[station_id],
                    key=lambda neighbor_id: _distance(
                        item.pos, input_map[neighbor_id].pos
                    ),
                )
            )
            index = order_index[station_id]
            contexts[station_id] = LocalLabelContext(
                station_id=station_id,
                dense=dense,
                cluster_id=cluster_id,
                corridor_axis=axis,
                corridor_index=index,
                preferred_directions=_preferred_directions(axis, index),
                tangent_vector=_tangent_vector(axis),
                nearby_stations=nearby,
            )

    return contexts
