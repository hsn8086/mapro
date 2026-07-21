from __future__ import annotations

import unittest

from map_gen.draw.lines import draw_lines
from map_gen.stroke_builder import StrokeSegment


class DrawStub:
    def __init__(self) -> None:
        self.line_calls: list[
            tuple[list[tuple[float, float]], str, int, str | None]
        ] = []
        self.polygon_calls: list[tuple[list[tuple[float, float]], str | None]] = []
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

    def polygon(
        self, points: list[tuple[float, float]], *, fill: str | None = None
    ) -> None:
        self.polygon_calls.append((points, fill))


class NativePathDrawStub(DrawStub):
    def __init__(self) -> None:
        super().__init__()
        self.path_calls: list[dict[str, object]] = []

    def path(
        self,
        d: str,
        *,
        fill: str | None = None,
        stroke: str | None = None,
        stroke_width: int | float = 1,
        stroke_linecap: str | None = None,
        stroke_linejoin: str | None = None,
    ) -> None:
        self.path_calls.append(
            {
                "d": d,
                "fill": fill,
                "stroke": stroke,
                "stroke_width": stroke_width,
                "stroke_linecap": stroke_linecap,
                "stroke_linejoin": stroke_linejoin,
            }
        )


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

        self.assertEqual(len(draw.polygon_calls), 3)
        self.assertEqual(draw.polygon_calls[0][1], "#ff0000")
        self.assertEqual(draw.polygon_calls[1][1], "#ff0000")
        self.assertEqual(draw.polygon_calls[2][1], "#ff0000")
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

        self.assertEqual(len(draw.polygon_calls), 2)
        self.assertEqual(draw.polygon_calls[0][1], "#cccccc")
        self.assertEqual(draw.polygon_calls[1][1], "#ff0000")

    def test_draw_lines_uses_native_stroke_path_when_backend_supports_it(self) -> None:
        draw = NativePathDrawStub()
        draw_lines(
            draw,
            [
                StrokeSegment("1", (10.0, 10.0), (20.0, 10.0), "#ff0000", 8.0, False),
                StrokeSegment("1", (20.0, 10.0), (20.0, 20.0), "#ff0000", 8.0, False),
            ],
        )

        self.assertEqual(len(draw.path_calls), 1)
        self.assertEqual(draw.path_calls[0]["stroke"], "#ff0000")
        self.assertEqual(draw.path_calls[0]["stroke_linecap"], "round")
        self.assertEqual(draw.path_calls[0]["stroke_linejoin"], "round")
        self.assertEqual(draw.polygon_calls, [])


if __name__ == "__main__":
    unittest.main()
