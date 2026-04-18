from __future__ import annotations

import unittest

from map_gen.stroke_builder import build_line_strokes


class StrokeBuilderTests(unittest.TestCase):
    def test_build_line_strokes_splits_shared_segment_into_parallel_offsets(
        self,
    ) -> None:
        strokes = build_line_strokes(
            {
                "1": [(0, 0), (10, 0)],
                "2": [(0, 0), (10, 0)],
            },
            {
                "1": {"points": [(0, 0), (10, 0)], "statuses": ["active", "active"]},
                "2": {"points": [(0, 0), (10, 0)], "statuses": ["active", "active"]},
            },
            {
                "1": {"id": "1", "color": "#ff0000", "type": "subway"},
                "2": {"id": "2", "color": "#00ff00", "type": "subway"},
            },
            {((0, 0), (10, 0)): ["1", "2"]},
            {((0, 0), (10, 0)): {"1": 0, "2": 1}},
            {"COLOR_INACTIVE": "#cccccc"},
            18.0,
        )

        self.assertEqual(len(strokes), 2)
        self.assertEqual(strokes[0].start, (0.0, -4.5))
        self.assertEqual(strokes[0].end, (10.0, -4.5))
        self.assertEqual(strokes[1].start, (0.0, 4.5))
        self.assertEqual(strokes[1].end, (10.0, 4.5))
        self.assertEqual(strokes[0].thickness, 10)
        self.assertEqual(strokes[1].thickness, 10)

    def test_build_line_strokes_marks_planned_segment_inactive(self) -> None:
        strokes = build_line_strokes(
            {"1": [(0, 0), (10, 0)]},
            {"1": {"points": [(0, 0), (10, 0)], "statuses": ["planned", "active"]}},
            {"1": {"id": "1", "color": "#ff0000", "type": "subway"}},
            {((0, 0), (10, 0)): ["1"]},
            {((0, 0), (10, 0)): {"1": 0}},
            {"COLOR_INACTIVE": "#cccccc"},
            18.0,
        )

        self.assertEqual(len(strokes), 1)
        self.assertTrue(strokes[0].is_inactive)
        self.assertEqual(strokes[0].color, "#cccccc")

    def test_build_line_strokes_reduces_single_tram_thickness(self) -> None:
        strokes = build_line_strokes(
            {"T": [(0, 0), (10, 0)]},
            {"T": {"points": [(0, 0), (10, 0)], "statuses": ["active", "active"]}},
            {"T": {"id": "T", "color": "#00bde2", "type": "tram"}},
            {((0, 0), (10, 0)): ["T"]},
            {((0, 0), (10, 0)): {"T": 0}},
            {"COLOR_INACTIVE": "#cccccc"},
            18.0,
        )

        self.assertEqual(len(strokes), 1)
        self.assertEqual(strokes[0].thickness, 9.0)


if __name__ == "__main__":
    unittest.main()
