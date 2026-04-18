from __future__ import annotations

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


def draw_lines(draw, stroke_segments: list[StrokeSegment]) -> None:
    grouped_paths = _group_stroke_paths(stroke_segments)
    draw_buffer_inactive = [path for path in grouped_paths if path[0].is_inactive]
    draw_buffer_active = [path for path in grouped_paths if not path[0].is_inactive]

    def execute_draw_buffer(buffer: list[list[StrokeSegment]]) -> None:
        for path in buffer:
            first_segment = path[0]
            col = first_segment.color
            thick = first_segment.thickness
            points: list[tuple[float, float]] = [first_segment.start, first_segment.end]

            for segment in path[1:]:
                points.extend([segment.start, segment.end])

            w = int(thick)
            draw.line(points, fill=col, width=w, joint="curve")

            r_cap = (thick - 1) / 2.0
            if r_cap < 0:
                r_cap = 0

            if thick > 2:
                start = path[0].start
                end = path[-1].end
                draw.ellipse(
                    [
                        start[0] - r_cap,
                        start[1] - r_cap,
                        start[0] + r_cap,
                        start[1] + r_cap,
                    ],
                    fill=col,
                )
                draw.ellipse(
                    [end[0] - r_cap, end[1] - r_cap, end[0] + r_cap, end[1] + r_cap],
                    fill=col,
                )

    execute_draw_buffer(draw_buffer_inactive)
    execute_draw_buffer(draw_buffer_active)
