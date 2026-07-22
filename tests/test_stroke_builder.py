from __future__ import annotations

import unittest

from map_gen.stroke_builder import StrokeArc, StrokeSegment, build_line_strokes


class StrokeBuilderTests(unittest.TestCase):
    def test_build_line_strokes_splits_shared_segment_into_parallel_offsets(
        self,
    ) -> None:
        key = ((0, 0), (10, 0))
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
            {key: ["1", "2"]},
            {("1", key): -4.5, ("2", key): 4.5},
            {"COLOR_INACTIVE": "#cccccc"},
            18.0,
        )

        self.assertEqual(len(strokes), 2)
        self.assertEqual(strokes[0].start, (0.0, -4.5))
        self.assertEqual(strokes[0].end, (10.0, -4.5))
        self.assertEqual(strokes[1].start, (0.0, 4.5))
        self.assertEqual(strokes[1].end, (10.0, 4.5))
        self.assertEqual(strokes[0].thickness, 18.0)
        self.assertEqual(strokes[1].thickness, 18.0)

    def test_build_line_strokes_marks_planned_segment_inactive(self) -> None:
        strokes = build_line_strokes(
            {"1": [(0, 0), (10, 0)]},
            {"1": {"points": [(0, 0), (10, 0)], "statuses": ["planned", "active"]}},
            {"1": {"id": "1", "color": "#ff0000", "type": "subway"}},
            {((0, 0), (10, 0)): ["1"]},
            {("1", ((0, 0), (10, 0))): 0.0},
            {"COLOR_INACTIVE": "#cccccc", "COLOR_STATUS_PLANNED": "#bbbbbb"},
            18.0,
        )

        self.assertEqual(len(strokes), 1)
        self.assertTrue(strokes[0].is_inactive)
        self.assertEqual(strokes[0].color, "#bbbbbb")

    def test_build_line_strokes_marks_under_construction_segment_inactive(self) -> None:
        strokes = build_line_strokes(
            {"1": [(0, 0), (10, 0)]},
            {
                "1": {
                    "points": [(0, 0), (10, 0)],
                    "statuses": ["under_construction", "active"],
                }
            },
            {"1": {"id": "1", "color": "#ff0000", "type": "subway"}},
            {((0, 0), (10, 0)): ["1"]},
            {},
            {
                "COLOR_INACTIVE": "#cccccc",
                "COLOR_STATUS_UNDER_CONSTRUCTION": "#aa8844",
            },
            18.0,
        )

        self.assertEqual(len(strokes), 1)
        self.assertTrue(strokes[0].is_inactive)
        self.assertEqual(strokes[0].color, "#aa8844")

    def test_build_line_strokes_reduces_single_tram_thickness(self) -> None:
        strokes = build_line_strokes(
            {"T": [(0, 0), (10, 0)]},
            {"T": {"points": [(0, 0), (10, 0)], "statuses": ["active", "active"]}},
            {"T": {"id": "T", "color": "#00bde2", "type": "tram"}},
            {((0, 0), (10, 0)): ["T"]},
            {},
            {"COLOR_INACTIVE": "#cccccc"},
            18.0,
        )

        self.assertEqual(len(strokes), 1)
        self.assertAlmostEqual(strokes[0].thickness, 18.0 * 0.55)

    def test_build_line_strokes_replaces_corner_with_arc(self) -> None:
        strokes = build_line_strokes(
            {"1": [(0, 0), (100, 0), (100, 100)]},
            {
                "1": {
                    "points": [(0, 0), (100, 0), (100, 100)],
                    "statuses": ["active", "active", "active"],
                }
            },
            {"1": {"id": "1", "color": "#ff0000", "type": "subway"}},
            {
                ((0, 0), (100, 0)): ["1"],
                ((100, 0), (100, 100)): ["1"],
            },
            {},
            {"COLOR_INACTIVE": "#cccccc", "CORNER_RADIUS": 10.0},
            8.0,
        )

        segments = [s for s in strokes if isinstance(s, StrokeSegment)]
        arcs = [s for s in strokes if isinstance(s, StrokeArc)]
        self.assertEqual(len(segments), 2)
        self.assertEqual(len(arcs), 1)

        arc = arcs[0]
        # the arc joins the trimmed segment ends continuously
        self.assertAlmostEqual(arc.start[0], segments[0].end[0], places=6)
        self.assertAlmostEqual(arc.start[1], segments[0].end[1], places=6)
        self.assertAlmostEqual(arc.end[0], segments[1].start[0], places=6)
        self.assertAlmostEqual(arc.end[1], segments[1].start[1], places=6)
        self.assertAlmostEqual(arc.radius, 10.0)

    def test_build_line_strokes_bundle_corner_arcs_share_center(self) -> None:
        polyline = [(0, 0), (100, 0), (100, 100)]
        key_h = ((0, 0), (100, 0))
        key_v = ((100, 0), (100, 100))
        strokes = build_line_strokes(
            {"A": list(polyline), "B": list(polyline)},
            {
                "A": {"points": list(polyline), "statuses": ["active"] * 3},
                "B": {"points": list(polyline), "statuses": ["active"] * 3},
            },
            {
                "A": {"id": "A", "color": "#ff0000", "type": "subway"},
                "B": {"id": "B", "color": "#0000ff", "type": "subway"},
            },
            {key_h: ["A", "B"], key_v: ["A", "B"]},
            {
                ("A", key_h): 10.0,
                ("A", key_v): 10.0,
                ("B", key_h): -10.0,
                ("B", key_v): -10.0,
            },
            {"COLOR_INACTIVE": "#cccccc", "CORNER_RADIUS": 12.0},
            8.0,
        )

        arcs = [s for s in strokes if isinstance(s, StrokeArc)]
        self.assertEqual(len(arcs), 2)
        self.assertAlmostEqual(arcs[0].center[0], arcs[1].center[0], places=6)
        self.assertAlmostEqual(arcs[0].center[1], arcs[1].center[1], places=6)
        # every stroke keeps its own radius so the offset bands stay parallel
        self.assertNotAlmostEqual(arcs[0].radius, arcs[1].radius)

    def test_build_line_strokes_inserts_45_degree_ramp_at_bundle_boundary(
        self,
    ) -> None:
        # straight line whose second segment is laterally offset (bundle
        # entry): the jog must be bridged by a 45-degree ramp, not a gap
        key = ((100, 0), (200, 0))
        strokes = build_line_strokes(
            {"1": [(0, 0), (100, 0), (200, 0)]},
            {
                "1": {
                    "points": [(0, 0), (100, 0), (200, 0)],
                    "statuses": ["active", "active", "active"],
                }
            },
            {"1": {"id": "1", "color": "#ff0000", "type": "subway"}},
            {key: ["1", "2"]},
            {("1", key): 20.0},
            {"COLOR_INACTIVE": "#cccccc"},
            18.0,
        )

        segments = [s for s in strokes if isinstance(s, StrokeSegment)]
        self.assertEqual(len(segments), 3)
        first, ramp, second = segments
        # the ramp bridges exactly from the trimmed flat run to the offset run
        self.assertEqual(ramp.start, first.end)
        self.assertEqual(ramp.end, second.start)
        dx = abs(ramp.end[0] - ramp.start[0])
        dy = abs(ramp.end[1] - ramp.start[1])
        self.assertAlmostEqual(dx, dy)
        self.assertGreater(dx, 0.0)

    def test_build_line_strokes_parallel_continuation_stays_unbroken(self) -> None:
        # equal offsets on both sides of a vertex: no ramp, no gap
        key_1 = ((0, 0), (100, 0))
        key_2 = ((100, 0), (200, 0))
        strokes = build_line_strokes(
            {"1": [(0, 0), (100, 0), (200, 0)]},
            {
                "1": {
                    "points": [(0, 0), (100, 0), (200, 0)],
                    "statuses": ["active", "active", "active"],
                }
            },
            {"1": {"id": "1", "color": "#ff0000", "type": "subway"}},
            {key_1: ["1", "2"], key_2: ["1", "2"]},
            {("1", key_1): 20.0, ("1", key_2): 20.0},
            {"COLOR_INACTIVE": "#cccccc"},
            18.0,
        )

        segments = [s for s in strokes if isinstance(s, StrokeSegment)]
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].end, segments[1].start)

    def test_stroke_arc_start_end_properties_follow_angles(self) -> None:
        arc = StrokeArc(
            line_id="1",
            center=(10.0, 20.0),
            radius=5.0,
            start_angle=0.0,
            end_angle=1.5707963267948966,
            clockwise=False,
            color="#ff0000",
            thickness=4.0,
            is_inactive=False,
        )

        self.assertAlmostEqual(arc.start[0], 15.0)
        self.assertAlmostEqual(arc.start[1], 20.0)
        self.assertAlmostEqual(arc.end[0], 10.0)
        self.assertAlmostEqual(arc.end[1], 25.0)


if __name__ == "__main__":
    unittest.main()
