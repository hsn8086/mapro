from __future__ import annotations

import math

from PIL import Image, ImageDraw

from ..stroke_builder import StrokeSegment


def _group_stroke_paths(
    stroke_segments: list[StrokeSegment],
) -> list[list[StrokeSegment]]:
    grouped_paths: list[list[StrokeSegment]] = []
    current_path: list[StrokeSegment] = []
    current_key: tuple[str, str, float, bool] | None = None

    for segment in stroke_segments:
        segment_key = (
            segment.line_id,
            segment.color,
            segment.thickness,
            segment.is_inactive,
        )
        if current_key != segment_key:
            if current_path:
                grouped_paths.append(current_path)
            current_path = [segment]
            current_key = segment_key
            continue

        current_path.append(segment)

    if current_path:
        grouped_paths.append(current_path)

    return grouped_paths


def _normalize(vector: tuple[float, float]) -> tuple[float, float]:
    length = math.hypot(vector[0], vector[1])
    if length == 0:
        return (0.0, 0.0)
    return (vector[0] / length, vector[1] / length)


def _distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def _cross(v1: tuple[float, float], v2: tuple[float, float]) -> float:
    return v1[0] * v2[1] - v1[1] * v2[0]


def _build_segment_polygon(
    start: tuple[float, float],
    end: tuple[float, float],
    half_width: float,
) -> list[tuple[float, float]] | None:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return None

    ux = dx / length
    uy = dy / length
    nx = -uy
    ny = ux
    return [
        (start[0] + nx * half_width, start[1] + ny * half_width),
        (end[0] + nx * half_width, end[1] + ny * half_width),
        (end[0] - nx * half_width, end[1] - ny * half_width),
        (start[0] - nx * half_width, start[1] - ny * half_width),
    ]


def _arc_points(
    center: tuple[float, float],
    radius: float,
    start_angle: float,
    end_angle: float,
    *,
    clockwise: bool,
) -> list[tuple[float, float]]:
    if clockwise:
        while end_angle >= start_angle:
            end_angle -= math.tau
    else:
        while end_angle <= start_angle:
            end_angle += math.tau

    angle_diff = end_angle - start_angle
    step_count = max(10, int(abs(angle_diff) * radius / 2.0))
    points: list[tuple[float, float]] = []
    for index in range(step_count + 1):
        t = index / step_count
        angle = start_angle + angle_diff * t
        points.append(
            (center[0] + math.cos(angle) * radius, center[1] + math.sin(angle) * radius)
        )
    return points


def _draw_round_join(
    draw,
    prev_segment: StrokeSegment,
    next_segment: StrokeSegment,
    *,
    scale_factor: int,
) -> None:
    center = (prev_segment.end[0] * scale_factor, prev_segment.end[1] * scale_factor)
    half_width = prev_segment.thickness * scale_factor / 2.0

    prev_dir = _normalize(
        (
            prev_segment.end[0] - prev_segment.start[0],
            prev_segment.end[1] - prev_segment.start[1],
        )
    )
    next_dir = _normalize(
        (
            next_segment.end[0] - next_segment.start[0],
            next_segment.end[1] - next_segment.start[1],
        )
    )
    if prev_dir == (0.0, 0.0) or next_dir == (0.0, 0.0):
        return

    turn = _cross(prev_dir, next_dir)
    if abs(turn) < 1e-6:
        return

    prev_normal = (-prev_dir[1], prev_dir[0])
    next_normal = (-next_dir[1], next_dir[0])
    if turn > 0:
        start_vec = (-prev_normal[0], -prev_normal[1])
        end_vec = (-next_normal[0], -next_normal[1])
        clockwise = False
    else:
        start_vec = prev_normal
        end_vec = next_normal
        clockwise = True

    start_angle = math.atan2(start_vec[1], start_vec[0])
    end_angle = math.atan2(end_vec[1], end_vec[0])
    arc = _arc_points(center, half_width, start_angle, end_angle, clockwise=clockwise)
    draw.polygon(arc + [center], fill=prev_segment.color)


def _scale_point(point: tuple[float, float], factor: int) -> tuple[float, float]:
    return (point[0] * factor, point[1] * factor)


def _draw_path(draw, path: list[StrokeSegment], scale_factor: int = 1) -> None:
    first_segment = path[0]
    color = first_segment.color
    half_width = first_segment.thickness * scale_factor / 2.0

    scaled_segments: list[StrokeSegment] = []
    for segment in path:
        scaled_segments.append(
            StrokeSegment(
                line_id=segment.line_id,
                start=_scale_point(segment.start, scale_factor),
                end=_scale_point(segment.end, scale_factor),
                color=segment.color,
                thickness=segment.thickness * scale_factor,
                is_inactive=segment.is_inactive,
            )
        )

    for segment in scaled_segments:
        polygon = _build_segment_polygon(segment.start, segment.end, half_width)
        if polygon is not None:
            draw.polygon(polygon, fill=color)

    for index in range(len(scaled_segments) - 1):
        current = scaled_segments[index]
        nxt = scaled_segments[index + 1]
        if _distance(current.end, nxt.start) <= 1e-6:
            _draw_round_join(draw, current, nxt, scale_factor=1)

    radius = max(0.0, (first_segment.thickness - 1) / 2.0) * scale_factor
    endpoints = [scaled_segments[0].start, scaled_segments[-1].end]
    for point in endpoints:
        draw.ellipse(
            [
                point[0] - radius,
                point[1] - radius,
                point[0] + radius,
                point[1] + radius,
            ],
            fill=color,
        )


def draw_lines(draw, stroke_segments: list[StrokeSegment]) -> None:
    grouped_paths = _group_stroke_paths(stroke_segments)
    draw_buffer_inactive = [path for path in grouped_paths if path[0].is_inactive]
    draw_buffer_active = [path for path in grouped_paths if not path[0].is_inactive]

    if hasattr(draw, "_image"):
        base_image = draw._image
        scale = 6
        line_layer = Image.new(
            "RGBA", (base_image.width * scale, base_image.height * scale), (0, 0, 0, 0)
        )
        layer_draw = ImageDraw.Draw(line_layer)

        for path in draw_buffer_inactive:
            _draw_path(layer_draw, path, scale)

        for path in draw_buffer_active:
            _draw_path(layer_draw, path, scale)

        downsampled = line_layer.resize(base_image.size, Image.Resampling.LANCZOS)
        base_image.paste(downsampled, (0, 0), downsampled)
        return

    for path in draw_buffer_inactive:
        _draw_path(draw, path)

    for path in draw_buffer_active:
        _draw_path(draw, path)
