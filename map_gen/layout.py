from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Layout:
    width: int
    height: int
    scale_factor: int
    get_pos: Callable[[str], tuple[int, int] | None]


@dataclass(frozen=True)
class Bounds:
    min_x: float
    max_x: float
    min_y: float
    max_y: float


def expand_bounds(
    bounds: Bounds,
    *,
    min_margin: float = 8.0,
    ratio: float = 0.02,
) -> Bounds:
    width = max(bounds.max_x - bounds.min_x, 1.0)
    height = max(bounds.max_y - bounds.min_y, 1.0)
    margin_x = max(width * ratio, min_margin)
    margin_y = max(height * ratio, min_margin)

    return Bounds(
        min_x=bounds.min_x - margin_x,
        max_x=bounds.max_x + margin_x,
        min_y=bounds.min_y - margin_y,
        max_y=bounds.max_y + margin_y,
    )


def calculate_station_bounds(stations: dict[str, Any]) -> Bounds:
    x_values: list[float] = []
    y_values: list[float] = []

    for station in stations.values():
        if not isinstance(station, dict):
            continue

        x = station.get("x")
        y = station.get("y")
        if isinstance(x, int | float) and isinstance(y, int | float):
            x_values.append(float(x))
            y_values.append(float(y))

    if not x_values or not y_values:
        raise ValueError("No valid station coordinates found")

    return Bounds(
        min_x=min(x_values),
        max_x=max(x_values),
        min_y=min(y_values),
        max_y=max(y_values),
    )


def resolve_layout_bounds(
    stations: dict[str, Any],
    viewport: dict[str, Any] | None = None,
) -> Bounds:
    if viewport is None:
        return calculate_station_bounds(stations)

    min_x = viewport.get("min_x")
    max_x = viewport.get("max_x")
    min_y = viewport.get("min_y")
    max_y = viewport.get("max_y")
    if (
        isinstance(min_x, int | float)
        and isinstance(max_x, int | float)
        and isinstance(min_y, int | float)
        and isinstance(max_y, int | float)
    ):
        return Bounds(
            min_x=float(min_x),
            max_x=float(max_x),
            min_y=float(min_y),
            max_y=float(max_y),
        )

    return calculate_station_bounds(stations)


def get_pos_transform(
    stations: dict[str, Any],
    *,
    viewport: dict[str, Any] | None = None,
    scale_factor: int = 2,
    padding: int = 150,
) -> Layout:
    bounds = resolve_layout_bounds(stations, viewport)
    if viewport is None:
        bounds = expand_bounds(bounds)

    min_x = bounds.min_x
    max_x = bounds.max_x
    min_y = bounds.min_y
    max_y = bounds.max_y

    base_width = int(max_x - min_x + 2 * padding)
    base_height = int(max_y - min_y + 2 * padding)

    width = base_width * scale_factor
    height = base_height * scale_factor

    def get_pos(station_id: str) -> tuple[int, int] | None:
        station = stations.get(station_id)
        if not station:
            return None
        lx = station["x"] - min_x + padding
        ly = station["y"] - min_y + padding
        return (int(lx * scale_factor), int(ly * scale_factor))

    return Layout(
        width=width,
        height=height,
        scale_factor=scale_factor,
        get_pos=get_pos,
    )
