from __future__ import annotations

import unittest

from map_gen.stroke_builder import (
    StrokeArc,
    StrokeSegment,
    build_active_segment_keys,
    build_line_strokes,
)


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

    def test_build_line_strokes_shared_track_edges_ride_half_width_beside(
        self,
    ) -> None:
        # guest runs a-b (own), b-c (shared), c-d (own): the shared edge
        # becomes a continuous half-width stroke on one side of the
        # partner's track, and the own edges stay disconnected
        polyline = [(0, 0), (10, 0), (20, 0), (30, 0)]
        strokes = build_line_strokes(
            {"G": polyline},
            {
                "G": {
                    "points": polyline,
                    "statuses": ["active", "active", "active", "active"],
                    "shared": [None, "H", "H", None],
                }
            },
            {"G": {"id": "G", "color": "#ff0000", "type": "subway"}},
            {},
            {},
            {
                "COLOR_INACTIVE": "#cccccc",
                "SHARED_TRACK_OVERLAY_WIDTH": 9.0,
                "SHARED_TRACK_OVERLAY_OFFSET": 4.5,
            },
            18.0,
        )

        solid = [
            s for s in strokes if isinstance(s, StrokeSegment) and not s.is_overlay
        ]
        self.assertEqual(len(solid), 2)
        self.assertEqual(solid[0].start, (0.0, 0.0))
        self.assertEqual(solid[0].end, (10.0, 0.0))
        self.assertEqual(solid[1].start, (20.0, 0.0))
        self.assertEqual(solid[1].end, (30.0, 0.0))

        overlays = [s for s in strokes if isinstance(s, StrokeSegment) and s.is_overlay]
        self.assertEqual(len(overlays), 1)
        overlay = overlays[0]
        # one continuous half-width stroke shifted half a slot sideways
        self.assertEqual(overlay.thickness, 9.0)
        self.assertEqual(overlay.color, "#ff0000")
        self.assertEqual(abs(overlay.start[1]), 4.5)
        self.assertEqual(overlay.start[1], overlay.end[1])
        self.assertEqual((overlay.start[0], overlay.end[0]), (10.0, 20.0))

    def test_build_line_strokes_shared_overlay_keeps_rounded_corner(self) -> None:
        # L-shaped shared run: the half-width stroke turns with a real arc
        polyline = [(0, 0), (30, 0), (30, 30)]
        strokes = build_line_strokes(
            {"G": polyline},
            {
                "G": {
                    "points": polyline,
                    "statuses": ["active", "active", "active"],
                    "shared": ["H", "H", "H"],
                }
            },
            {"G": {"id": "G", "color": "#ff0000", "type": "subway"}},
            {},
            {},
            {
                "CORNER_RADIUS": 5.0,
                "SHARED_TRACK_OVERLAY_WIDTH": 9.0,
                "SHARED_TRACK_OVERLAY_OFFSET": 4.5,
            },
            18.0,
        )

        overlay_arcs = [s for s in strokes if isinstance(s, StrokeArc) and s.is_overlay]
        self.assertEqual(len(overlay_arcs), 1)
        self.assertEqual(overlay_arcs[0].thickness, 9.0)

    def test_build_line_strokes_shared_overlay_rides_partner_bundle_offset(
        self,
    ) -> None:
        key = ((0, 0), (10, 0))
        strokes = build_line_strokes(
            {"G": [(0, 0), (10, 0)]},
            {
                "G": {
                    "points": [(0, 0), (10, 0)],
                    "statuses": ["active", "active"],
                    "shared": ["H", "H"],
                }
            },
            {"G": {"id": "G", "color": "#ff0000", "type": "subway"}},
            {},
            {("H", key): 4.0},
            {
                "SHARED_TRACK_OVERLAY_WIDTH": 9.0,
                "SHARED_TRACK_OVERLAY_OFFSET": 4.5,
            },
            18.0,
        )

        overlays = [s for s in strokes if isinstance(s, StrokeSegment) and s.is_overlay]
        self.assertEqual(len(overlays), 1)
        # partner lateral 4.0 plus half-slot 4.5 along the same normal
        self.assertEqual(overlays[0].start[1], 8.5)

    def test_build_active_segment_keys_skips_shared_track_edges(self) -> None:
        polyline = [(0, 0), (10, 0), (20, 0)]
        active = build_active_segment_keys(
            {"G": polyline},
            {
                "G": {
                    "points": polyline,
                    "statuses": ["active", "active", "active"],
                    "shared": [None, "H", "H"],
                }
            },
            {"G": {"id": "G", "color": "#ff0000"}},
        )

        self.assertEqual(active, {((0, 0), (10, 0))})

    def test_build_active_segment_keys_excludes_inactive_portions(self) -> None:
        active = build_active_segment_keys(
            {
                "1": [(0, 0), (10, 0), (20, 0)],
                "2": [(0, 10), (10, 10)],
            },
            {
                "1": {
                    "points": [(0, 0), (10, 0), (20, 0)],
                    "statuses": ["active", "active", "under_construction"],
                },
                "2": {"points": [(0, 10), (10, 10)], "statuses": ["active", "active"]},
            },
            {
                "1": {"id": "1", "color": "#ff0000", "type": "subway"},
                "2": {
                    "id": "2",
                    "color": "#00ff00",
                    "type": "subway",
                    "status": "planned",
                },
            },
        )

        self.assertIn(((0, 0), (10, 0)), active)
        # segment adjacent to an under-construction station is inactive
        self.assertNotIn(((10, 0), (20, 0)), active)
        # whole line planned: nothing active
        self.assertNotIn(((0, 10), (10, 10)), active)

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
