from __future__ import annotations

import math
from dataclasses import dataclass

Point = tuple[int, int]
FloatPoint = tuple[float, float]
SegmentKey = tuple[Point, Point]


@dataclass(frozen=True)
class StationSymbol:
    """Resolved geometry for one station symbol.

    kind:
      slot    - inset background dot inside the stroke; edges stay solid
      ring    - white-core ink ring (single-stroke interchange)
      capsule - ink-outlined capsule spanning every stroke of a bundle
    """

    kind: str
    pos: FloatPoint
    normal: FloatPoint
    lat_min: float
    lat_max: float
    slot_width: float
    breadth: float
    ring_radius: float
    ring_stroke: float
    bbox: tuple[float, float, float, float]


def _normalize(dx: float, dy: float) -> FloatPoint:
    length = math.hypot(dx, dy)
    if length == 0:
        return (0.0, 0.0)
    return (dx / length, dy / length)


def _point_on_segment(p: Point, a: Point, b: Point) -> bool:
    dx1, dy1 = b[0] - a[0], b[1] - a[1]
    dx2, dy2 = p[0] - a[0], p[1] - a[1]
    if dx1 * dy2 - dx2 * dy1 != 0:
        return False
    dot = dx1 * dx2 + dy1 * dy2
    if dot < 0:
        return False
    return dot <= dx1 * dx1 + dy1 * dy1


def _axis_from(a: Point, b: Point) -> tuple[FloatPoint, SegmentKey]:
    key = (b, a) if a > b else (a, b)
    direction = _normalize(key[1][0] - key[0][0], key[1][1] - key[0][1])
    return ((-direction[1], direction[0]), key)


def find_station_axes(
    pos: Point,
    station_line_ids: list[str],
    line_polylines: dict[str, list[Point]],
) -> list[tuple[FloatPoint, SegmentKey]]:
    """All candidate segments carrying the station, own lines first.

    The normal is the canonical-direction left normal of each segment, the
    same frame used by bundle offsets. Stations compressed into a straight
    run are matched by point-on-segment containment.
    """
    candidates = list(station_line_ids) + [
        lid for lid in line_polylines if lid not in station_line_ids
    ]
    axes: list[tuple[FloatPoint, SegmentKey]] = []
    seen: set[SegmentKey] = set()

    def add(a: Point, b: Point) -> None:
        axis = _axis_from(a, b)
        if axis[1] not in seen:
            seen.add(axis[1])
            axes.append(axis)

    for line_id in candidates:
        polyline = line_polylines.get(line_id, [])
        for index, point in enumerate(polyline):
            if point != pos:
                continue
            if index + 1 < len(polyline) and polyline[index + 1] != pos:
                add(pos, polyline[index + 1])
            if index > 0 and polyline[index - 1] != pos:
                add(pos, polyline[index - 1])
    if not axes:
        for line_id in candidates:
            polyline = line_polylines.get(line_id, [])
            for index in range(len(polyline) - 1):
                if _point_on_segment(pos, polyline[index], polyline[index + 1]):
                    add(polyline[index], polyline[index + 1])
    return axes


def find_station_axis(
    pos: Point,
    station_line_ids: list[str],
    line_polylines: dict[str, list[Point]],
) -> tuple[FloatPoint, SegmentKey] | None:
    """First candidate axis (see find_station_axes)."""
    axes = find_station_axes(pos, station_line_ids, line_polylines)
    return axes[0] if axes else None


def build_station_symbol(
    pos: Point | FloatPoint,
    *,
    is_transfer: bool,
    normal: FloatPoint,
    laterals: list[float],
    styles: dict[str, float | str],
) -> StationSymbol:
    line_width = float(styles["LINE_WIDTH"])
    slot_width = float(styles.get("STATION_SLOT_WIDTH", line_width * 0.35))
    dot_radius = float(styles.get("STATION_DOT_RADIUS", line_width * 0.26))
    ring_radius = float(styles.get("TRANSFER_RING_RADIUS", line_width * 0.55))
    ring_stroke = float(styles.get("TRANSFER_RING_STROKE", line_width * 0.16))

    lat_min = min(laterals) if laterals else 0.0
    lat_max = max(laterals) if laterals else 0.0
    span = lat_max - lat_min

    if is_transfer:
        kind = "capsule" if span > 1e-6 else "ring"
    else:
        kind = "slot"

    breadth = span + dot_radius * 2.0
    center = (
        pos[0] + normal[0] * (lat_min + lat_max) / 2.0,
        pos[1] + normal[1] * (lat_min + lat_max) / 2.0,
    )

    if kind == "ring":
        extent = ring_radius + ring_stroke
        bbox = (
            pos[0] - extent,
            pos[1] - extent,
            pos[0] + extent,
            pos[1] + extent,
        )
    elif kind == "capsule":
        end_a = (pos[0] + normal[0] * lat_min, pos[1] + normal[1] * lat_min)
        end_b = (pos[0] + normal[0] * lat_max, pos[1] + normal[1] * lat_max)
        extent = ring_radius + ring_stroke
        bbox = (
            min(end_a[0], end_b[0]) - extent,
            min(end_a[1], end_b[1]) - extent,
            max(end_a[0], end_b[0]) + extent,
            max(end_a[1], end_b[1]) + extent,
        )
    else:
        bbox = (
            center[0] - dot_radius,
            center[1] - dot_radius,
            center[0] + dot_radius,
            center[1] + dot_radius,
        )

    return StationSymbol(
        kind=kind,
        pos=(float(pos[0]), float(pos[1])),
        normal=normal,
        lat_min=lat_min,
        lat_max=lat_max,
        slot_width=slot_width,
        breadth=breadth,
        ring_radius=ring_radius,
        ring_stroke=ring_stroke,
        bbox=bbox,
    )


def _capsule_polygon(
    end_a: FloatPoint,
    end_b: FloatPoint,
    radius: float,
    *,
    samples: int = 20,
) -> list[FloatPoint]:
    axis = _normalize(end_b[0] - end_a[0], end_b[1] - end_a[1])
    if axis == (0.0, 0.0):
        axis = (1.0, 0.0)
    theta = math.atan2(axis[1], axis[0])
    points: list[FloatPoint] = []
    # semicircle around end_b (from theta-90 to theta+90)
    for step in range(samples + 1):
        angle = theta - math.pi / 2 + math.pi * step / samples
        points.append(
            (
                end_b[0] + math.cos(angle) * radius,
                end_b[1] + math.sin(angle) * radius,
            )
        )
    # semicircle around end_a (from theta+90 to theta+270)
    for step in range(samples + 1):
        angle = theta + math.pi / 2 + math.pi * step / samples
        points.append(
            (
                end_a[0] + math.cos(angle) * radius,
                end_a[1] + math.sin(angle) * radius,
            )
        )
    return points


def render_station_symbol(
    draw,
    symbol: StationSymbol,
    styles: dict[str, float | str],
) -> None:
    background = str(styles.get("COLOR_BG", "#FAFAF7"))
    ink = str(styles.get("COLOR_INK", styles.get("COLOR_STATION_STROKE", "#1A1A1A")))

    if symbol.kind == "slot":
        # inset background dot: the stroke edges stay solid so the line
        # never reads as cut through
        center = (
            symbol.pos[0] + symbol.normal[0] * (symbol.lat_min + symbol.lat_max) / 2.0,
            symbol.pos[1] + symbol.normal[1] * (symbol.lat_min + symbol.lat_max) / 2.0,
        )
        radius = symbol.breadth / 2.0
        draw.ellipse(
            [
                center[0] - radius,
                center[1] - radius,
                center[0] + radius,
                center[1] + radius,
            ],
            fill=background,
            outline=None,
            width=0,
        )
        return

    if symbol.kind == "ring":
        radius = symbol.ring_radius
        draw.ellipse(
            [
                symbol.pos[0] - radius,
                symbol.pos[1] - radius,
                symbol.pos[0] + radius,
                symbol.pos[1] + radius,
            ],
            fill=background,
            outline=ink,
            width=int(round(symbol.ring_stroke)),
        )
        return

    end_a = (
        symbol.pos[0] + symbol.normal[0] * symbol.lat_min,
        symbol.pos[1] + symbol.normal[1] * symbol.lat_min,
    )
    end_b = (
        symbol.pos[0] + symbol.normal[0] * symbol.lat_max,
        symbol.pos[1] + symbol.normal[1] * symbol.lat_max,
    )
    outer = _capsule_polygon(end_a, end_b, symbol.ring_radius)
    inner = _capsule_polygon(end_a, end_b, symbol.ring_radius - symbol.ring_stroke)
    draw.polygon(outer, fill=ink)
    draw.polygon(inner, fill=background)
