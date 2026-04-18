from __future__ import annotations

from ..stroke_builder import StrokeSegment


def draw_lines(draw, stroke_segments: list[StrokeSegment]) -> None:
    draw_buffer_inactive = [
        segment for segment in stroke_segments if segment.is_inactive
    ]
    draw_buffer_active = [
        segment for segment in stroke_segments if not segment.is_inactive
    ]

    def execute_draw_buffer(buffer: list[StrokeSegment]) -> None:
        for segment in buffer:
            p1 = segment.start
            p2 = segment.end
            col = segment.color
            thick = segment.thickness
            w = int(thick)
            draw.line([p1, p2], fill=col, width=w)

            r_cap = (thick - 1) / 2.0
            if r_cap < 0:
                r_cap = 0

            if thick > 2:
                draw.ellipse(
                    [p1[0] - r_cap, p1[1] - r_cap, p1[0] + r_cap, p1[1] + r_cap],
                    fill=col,
                )
                draw.ellipse(
                    [p2[0] - r_cap, p2[1] - r_cap, p2[0] + r_cap, p2[1] + r_cap],
                    fill=col,
                )

    execute_draw_buffer(draw_buffer_inactive)
    execute_draw_buffer(draw_buffer_active)
