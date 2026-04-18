from __future__ import annotations

import unittest

from map_gen.draw.lines import draw_lines
from map_gen.stroke_builder import StrokeSegment


class DrawStub:
    def __init__(self) -> None:
        self.line_calls: list[
            tuple[list[tuple[float, float]], str, int, str | None]
        ] = []
        self.ellipse_calls: list[tuple[list[float], str | None]] = []

    def line(
        self,
        points: list[tuple[float, float]],
        *,
        fill: str,
        width: int,
        joint: str | None = None,
    ) -> None:
        self.line_calls.append((points, fill, width, joint))

    def ellipse(self, bounds: list[float], *, fill: str | None = None) -> None:
        self.ellipse_calls.append((bounds, fill))


class DrawLinesTests(unittest.TestCase):
    def test_draw_lines_groups_consecutive_segments_into_curved_path(self) -> None:
        draw = DrawStub()
        draw_lines(
            draw,
            [
                StrokeSegment("1", (10.0, 10.0), (20.0, 10.0), "#ff0000", 8.0, False),
                StrokeSegment("1", (20.0, 10.0), (20.0, 20.0), "#ff0000", 8.0, False),
            ],
        )

        self.assertEqual(len(draw.line_calls), 1)
        points, fill, width, joint = draw.line_calls[0]
        self.assertEqual(
            points,
            [(10.0, 10.0), (20.0, 10.0), (20.0, 10.0), (20.0, 20.0)],
        )
        self.assertEqual(fill, "#ff0000")
        self.assertEqual(width, 8)
        self.assertEqual(joint, "curve")
        self.assertEqual(len(draw.ellipse_calls), 2)

    def test_draw_lines_still_draws_inactive_paths_first(self) -> None:
        draw = DrawStub()
        draw_lines(
            draw,
            [
                StrokeSegment("1", (0.0, 0.0), (10.0, 0.0), "#ff0000", 8.0, False),
                StrokeSegment("2", (0.0, 5.0), (10.0, 5.0), "#cccccc", 8.0, True),
            ],
        )

        self.assertEqual(len(draw.line_calls), 2)
        self.assertEqual(draw.line_calls[0][1], "#cccccc")
        self.assertEqual(draw.line_calls[1][1], "#ff0000")


if __name__ == "__main__":
    unittest.main()
