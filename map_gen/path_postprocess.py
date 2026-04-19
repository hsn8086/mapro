from __future__ import annotations

from .geometry import get_dir

Point = tuple[int, int]


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


def postprocess_polyline(points: list[Point]) -> list[Point]:
    return compress_collinear_points(points)
