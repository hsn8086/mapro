from __future__ import annotations

import unittest

from map_gen.station_badges import collect_facility_tags, draw_badges, measure_badges


class DrawStub:
    def __init__(self) -> None:
        self.rectangles: list[tuple[list[float], str | None]] = []
        self.texts: list[tuple[tuple[float, float], str, str]] = []

    def textbbox(
        self, _pos: tuple[int, int], text: str, font=None
    ) -> tuple[int, int, int, int]:
        _ = font
        return (0, 0, len(text) * 4, 6)

    def rectangle(self, bounds: list[float], fill=None, outline=None, width=0) -> None:
        _ = outline, width
        self.rectangles.append((bounds, fill))

    def rounded_rectangle(
        self,
        bounds: list[float],
        fill=None,
        outline=None,
        width=0,
        radius=0,
    ) -> None:
        _ = outline, width, radius
        self.rectangles.append((bounds, fill))

    def text(self, pos: tuple[float, float], text: str, fill: str, font=None) -> None:
        _ = font
        self.texts.append((pos, text, fill))


class StationBadgesTests(unittest.TestCase):
    def test_collect_facility_tags_picks_first_toilet_location(self) -> None:
        station = {
            "facilities": [
                {"type": "shop"},
                {"type": "toilet", "description": {"location": "outside"}},
                {"type": "toilet", "description": {"location": "inside"}},
            ]
        }

        self.assertEqual(collect_facility_tags(station), ["toilet_outside"])

    def test_measure_badges_returns_expected_width_and_height(self) -> None:
        draw = DrawStub()
        metrics = measure_badges(
            draw,
            [{"line_id": "1", "texts": ["01"], "color": "#ff0000", "active": True}],
            ["toilet_inside"],
            [],
            1,
        )

        self.assertEqual(metrics.primary.width, 44.0)
        self.assertEqual(metrics.primary.height, 8.0)
        self.assertEqual(metrics.compact.width, 0.0)
        self.assertEqual(metrics.compact.height, 0.0)

    def test_draw_badges_renders_marker_blocks_and_facility_text(self) -> None:
        draw = DrawStub()
        draw_badges(
            draw,
            start_x=20.0,
            marker_y=30.0,
            line_markers=[
                {"line_id": "1", "texts": ["01"], "color": "#ff0000", "active": True},
                {"line_id": "2", "texts": ["快"], "color": "#00ff00", "active": False},
            ],
            facility_tags=["toilet_outside"],
            font_paths=[],
            scale_factor=1,
            inactive_color="#cccccc",
        )

        self.assertEqual(len(draw.rectangles), 3)
        self.assertEqual(draw.rectangles[0][1], "#ff0000")
        self.assertEqual(draw.rectangles[1][1], "#cccccc")
        self.assertEqual(draw.rectangles[2][1], "#e8f1ff")
        rendered_texts = [item[1] for item in draw.texts]
        self.assertIn("1", rendered_texts)
        self.assertIn("01", rendered_texts)
        self.assertIn("2", rendered_texts)
        self.assertIn("快", rendered_texts)
        self.assertIn("WC", rendered_texts)


if __name__ == "__main__":
    unittest.main()
