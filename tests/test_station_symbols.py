from __future__ import annotations

import math
import unittest

from map_gen.draw.stations import (
    _choose_station_axis,
    _closest_point_on_stroke,
    _corner_symbol_pose,
    _station_track_points,
)
from map_gen.station_symbols import (
    build_station_symbol,
    find_station_axes,
    find_station_axis,
    fit_junction_spread,
    render_station_symbol,
)
from map_gen.stroke_builder import StrokeArc, StrokeSegment

STYLES: dict[str, float | str] = {
    "LINE_WIDTH": 8.0,
    "STATION_SLOT_WIDTH": 3.0,
    "STATION_SLOT_BREADTH": 4.0,
    "TRANSFER_RING_RADIUS": 5.0,
    "TRANSFER_RING_STROKE": 1.5,
    "COLOR_BG": "#fafaf7",
    "COLOR_INK": "#1a1a1a",
}


class SymbolDrawStub:
    def __init__(self) -> None:
        self.line_calls: list[dict] = []
        self.ellipse_calls: list[dict] = []
        self.polygon_calls: list[dict] = []

    def line(self, points, *, fill, width) -> None:
        self.line_calls.append({"points": points, "fill": fill, "width": width})

    def ellipse(self, bounds, *, fill, outline, width) -> None:
        self.ellipse_calls.append(
            {"bounds": bounds, "fill": fill, "outline": outline, "width": width}
        )

    def polygon(self, points, *, fill) -> None:
        self.polygon_calls.append({"points": points, "fill": fill})


class FindStationAxisTests(unittest.TestCase):
    def test_matches_polyline_vertex(self) -> None:
        axis = find_station_axis(
            (10, 0),
            ["1"],
            {"1": [(0, 0), (10, 0), (20, 0)]},
        )

        self.assertIsNotNone(axis)
        assert axis is not None
        normal, key = axis
        self.assertEqual(normal, (0.0, 1.0))
        self.assertIn(key, (((0, 0), (10, 0)), ((10, 0), (20, 0))))

    def test_matches_point_lying_on_segment(self) -> None:
        # station compressed into a straight run: not a vertex, but on-segment
        axis = find_station_axis(
            (10, 0),
            ["1"],
            {"1": [(0, 0), (20, 0)]},
        )

        self.assertIsNotNone(axis)
        assert axis is not None
        normal, key = axis
        self.assertEqual(normal, (0.0, 1.0))
        self.assertEqual(key, ((0, 0), (20, 0)))

    def test_vertical_segment_axis_normal_points_left_of_canonical(self) -> None:
        axis = find_station_axis(
            (0, 10),
            ["1"],
            {"1": [(0, 0), (0, 20)]},
        )

        self.assertIsNotNone(axis)
        assert axis is not None
        normal, _ = axis
        self.assertEqual(normal, (-1.0, 0.0))

    def test_returns_none_when_station_off_every_line(self) -> None:
        self.assertIsNone(find_station_axis((99, 99), ["1"], {"1": [(0, 0), (10, 0)]}))

    def test_find_station_axes_returns_every_segment_at_corner_vertex(self) -> None:
        axes = find_station_axes(
            (10, 0),
            ["1"],
            {"1": [(0, 0), (10, 0), (10, 10)]},
        )

        keys = {key for _, key in axes}
        self.assertEqual(keys, {((0, 0), (10, 0)), ((10, 0), (10, 10))})


class ChooseStationAxisTests(unittest.TestCase):
    def test_prefers_axis_with_widest_lateral_span_of_own_lines(self) -> None:
        # station sits at a corner: its own line turns, but the bundle
        # corridor (with the offset partner) must win the axis choice
        h_key = ((0, 0), (10, 0))
        v_key = ((10, 0), (10, 10))
        result = _choose_station_axis(
            (10, 0),
            ["1", "2"],
            {
                "1": [(0, 0), (10, 0), (10, 10)],
                "2": [(0, 0), (10, 0), (20, 0)],
            },
            {h_key: ["1", "2"], v_key: ["1"]},
            {("1", h_key): 0.0, ("2", h_key): 8.0},
        )

        self.assertIsNotNone(result)
        assert result is not None
        _, key, laterals = result
        self.assertEqual(key, h_key)
        self.assertEqual(sorted(laterals), [0.0, 8.0])

    def test_laterals_only_include_own_lines(self) -> None:
        # non-transfer station on a shared segment: the slot must sit in
        # its own line's offset stroke, not span every member of the bundle
        key = ((0, 0), (10, 0))
        result = _choose_station_axis(
            (5, 0),
            ["2"],
            {
                "1": [(0, 0), (10, 0)],
                "2": [(0, 0), (10, 0)],
            },
            {key: ["1", "2"]},
            {("1", key): 0.0, ("2", key): 8.0},
        )

        self.assertIsNotNone(result)
        assert result is not None
        _, _, laterals = result
        self.assertEqual(laterals, [8.0])


class CornerSymbolPoseTests(unittest.TestCase):
    def test_station_on_right_angle_corner_moves_to_arc_midpoint(self) -> None:
        # line travels east then turns south at (100, 0)
        pose = _corner_symbol_pose(
            (100, 0),
            ["1"],
            {"1": [(0, 0), (100, 0), (100, 100)]},
            10.0,
        )

        self.assertIsNotNone(pose)
        assert pose is not None
        midpoint, radial, tangent_dir = pose
        # arc centre sits at (90, 10); midpoint is pulled diagonally inward
        self.assertLess(midpoint[0], 100.0)
        self.assertGreater(midpoint[1], 0.0)
        self.assertAlmostEqual(math.hypot(midpoint[0] - 90.0, midpoint[1] - 10.0), 10.0)
        # radial points outward, away from the corner centre
        self.assertGreater(radial[0], 0.0)
        self.assertLess(radial[1], 0.0)
        self.assertEqual(tangent_dir, (1, 1))

    def test_station_on_straight_run_has_no_corner_pose(self) -> None:
        pose = _corner_symbol_pose(
            (50, 0),
            ["1"],
            {"1": [(0, 0), (50, 0), (100, 0)]},
            10.0,
        )

        self.assertIsNone(pose)


class BuildStationSymbolTests(unittest.TestCase):
    def test_non_transfer_station_gets_slot(self) -> None:
        symbol = build_station_symbol(
            (10, 10),
            is_transfer=False,
            normal=(0.0, 1.0),
            laterals=[0.0],
            styles=STYLES,
        )

        self.assertEqual(symbol.kind, "slot")

    def test_transfer_on_single_stroke_gets_ring(self) -> None:
        symbol = build_station_symbol(
            (10, 10),
            is_transfer=True,
            normal=(0.0, 1.0),
            laterals=[0.0],
            styles=STYLES,
        )

        self.assertEqual(symbol.kind, "ring")

    def test_transfer_spanning_bundle_gets_capsule(self) -> None:
        symbol = build_station_symbol(
            (10, 10),
            is_transfer=True,
            normal=(0.0, 1.0),
            laterals=[-9.0, 0.0, 9.0],
            styles=STYLES,
        )

        self.assertEqual(symbol.kind, "capsule")
        self.assertEqual(symbol.lat_min, -9.0)
        self.assertEqual(symbol.lat_max, 9.0)

    def test_slot_breadth_covers_lateral_span(self) -> None:
        narrow = build_station_symbol(
            (10, 10),
            is_transfer=False,
            normal=(0.0, 1.0),
            laterals=[0.0],
            styles=STYLES,
        )
        wide = build_station_symbol(
            (10, 10),
            is_transfer=False,
            normal=(0.0, 1.0),
            laterals=[-9.0, 9.0],
            styles=STYLES,
        )

        self.assertGreater(wide.breadth, narrow.breadth)
        self.assertAlmostEqual(wide.breadth - narrow.breadth, 18.0)


class RenderStationSymbolTests(unittest.TestCase):
    def test_slot_renders_inset_background_dot(self) -> None:
        draw = SymbolDrawStub()
        symbol = build_station_symbol(
            (10, 10),
            is_transfer=False,
            normal=(0.0, 1.0),
            laterals=[0.0],
            styles=STYLES,
        )

        render_station_symbol(draw, symbol, STYLES)

        self.assertEqual(len(draw.ellipse_calls), 1)
        call = draw.ellipse_calls[0]
        self.assertEqual(call["fill"], "#fafaf7")
        self.assertIsNone(call["outline"])
        # dot must stay strictly inside the stroke: diameter < LINE_WIDTH
        left, top, right, bottom = call["bounds"]
        self.assertLess(right - left, float(STYLES["LINE_WIDTH"]))
        self.assertEqual(draw.line_calls, [])
        self.assertEqual(draw.polygon_calls, [])

    def test_slot_dot_centres_inside_offset_stroke(self) -> None:
        draw = SymbolDrawStub()
        symbol = build_station_symbol(
            (10, 10),
            is_transfer=False,
            normal=(0.0, 1.0),
            laterals=[6.0],
            styles=STYLES,
        )

        render_station_symbol(draw, symbol, STYLES)

        left, top, right, bottom = draw.ellipse_calls[0]["bounds"]
        self.assertAlmostEqual((top + bottom) / 2.0, 16.0)
        self.assertAlmostEqual((left + right) / 2.0, 10.0)

    def test_ring_renders_single_ellipse_with_ink_outline(self) -> None:
        draw = SymbolDrawStub()
        symbol = build_station_symbol(
            (10, 10),
            is_transfer=True,
            normal=(0.0, 1.0),
            laterals=[0.0],
            styles=STYLES,
        )

        render_station_symbol(draw, symbol, STYLES)

        self.assertEqual(len(draw.ellipse_calls), 1)
        call = draw.ellipse_calls[0]
        self.assertEqual(call["fill"], "#fafaf7")
        self.assertEqual(call["outline"], "#1a1a1a")
        self.assertEqual(draw.line_calls, [])
        self.assertEqual(draw.polygon_calls, [])

    def test_capsule_renders_outer_ink_and_inner_background_polygons(self) -> None:
        draw = SymbolDrawStub()
        symbol = build_station_symbol(
            (10, 10),
            is_transfer=True,
            normal=(0.0, 1.0),
            laterals=[-9.0, 9.0],
            styles=STYLES,
        )

        render_station_symbol(draw, symbol, STYLES)

        self.assertEqual(len(draw.polygon_calls), 2)
        self.assertEqual(draw.polygon_calls[0]["fill"], "#1a1a1a")
        self.assertEqual(draw.polygon_calls[1]["fill"], "#fafaf7")
        self.assertEqual(draw.line_calls, [])
        self.assertEqual(draw.ellipse_calls, [])


class FitJunctionSpreadTests(unittest.TestCase):
    def test_returns_axis_and_laterals_for_collinear_tracks(self) -> None:
        result = fit_junction_spread(
            (100.0, 100.0),
            [(94.0, 94.0), (100.0, 100.0), (106.0, 106.0)],
            tolerance=2.0,
            min_span=7.0,
        )

        self.assertIsNotNone(result)
        assert result is not None
        axis, laterals = result
        self.assertAlmostEqual(abs(axis[0]), math.sqrt(0.5), places=6)
        self.assertAlmostEqual(abs(axis[1]), math.sqrt(0.5), places=6)
        self.assertAlmostEqual(min(laterals), -max(laterals), places=6)
        self.assertAlmostEqual(max(laterals) - min(laterals), math.hypot(12.0, 12.0))

    def test_returns_none_when_spread_stays_within_min_span(self) -> None:
        self.assertIsNone(
            fit_junction_spread(
                (100.0, 100.0),
                [(98.0, 98.0), (100.0, 100.0), (102.0, 102.0)],
                tolerance=2.0,
                min_span=7.0,
            )
        )

    def test_returns_none_when_tracks_are_not_collinear(self) -> None:
        self.assertIsNone(
            fit_junction_spread(
                (100.0, 100.0),
                [(94.0, 94.0), (100.0, 90.0), (106.0, 106.0)],
                tolerance=2.0,
                min_span=7.0,
            )
        )

    def test_returns_none_when_station_is_off_the_fitted_line(self) -> None:
        self.assertIsNone(
            fit_junction_spread(
                (100.0, 130.0),
                [(94.0, 94.0), (100.0, 100.0), (106.0, 106.0)],
                tolerance=2.0,
                min_span=7.0,
            )
        )

    def test_returns_none_for_a_single_track(self) -> None:
        self.assertIsNone(
            fit_junction_spread(
                (100.0, 100.0),
                [(100.0, 100.0)],
                tolerance=2.0,
                min_span=7.0,
            )
        )


class ClosestPointOnStrokeTests(unittest.TestCase):
    def test_projects_onto_a_segment(self) -> None:
        segment = StrokeSegment(
            line_id="1",
            start=(0.0, 10.0),
            end=(20.0, 10.0),
            color="#000000",
            thickness=8.0,
            is_inactive=False,
        )

        self.assertEqual(_closest_point_on_stroke(segment, (5.0, 0.0)), (5.0, 10.0))

    def test_clamps_to_segment_ends(self) -> None:
        segment = StrokeSegment(
            line_id="1",
            start=(0.0, 0.0),
            end=(10.0, 0.0),
            color="#000000",
            thickness=8.0,
            is_inactive=False,
        )

        self.assertEqual(_closest_point_on_stroke(segment, (50.0, 0.0)), (10.0, 0.0))

    def test_follows_the_drawn_winding_of_a_clockwise_arc(self) -> None:
        # the long way round: from due east clockwise to due north, so the
        # arc passes through due west. Sampling the short way instead would
        # never reach that side of the circle.
        arc = StrokeArc(
            line_id="1",
            center=(0.0, 0.0),
            radius=10.0,
            start_angle=0.0,
            end_angle=math.pi / 2,
            clockwise=True,
            color="#000000",
            thickness=8.0,
            is_inactive=False,
        )

        closest = _closest_point_on_stroke(arc, (-30.0, 0.0))

        self.assertAlmostEqual(closest[0], -10.0, places=6)
        self.assertAlmostEqual(closest[1], 0.0, places=6)

    def test_follows_the_drawn_winding_of_a_counterclockwise_arc(self) -> None:
        arc = StrokeArc(
            line_id="1",
            center=(120.0, 120.0),
            radius=20.0,
            start_angle=math.pi,
            end_angle=-math.pi / 2,
            clockwise=False,
            color="#000000",
            thickness=8.0,
            is_inactive=False,
        )

        closest = _closest_point_on_stroke(arc, (100.0, 100.0))

        self.assertAlmostEqual(closest[0], 120.0 - 20.0 * math.sqrt(0.5), places=2)
        self.assertAlmostEqual(closest[1], 120.0 - 20.0 * math.sqrt(0.5), places=2)


def _turning_line(
    line_id: str,
    *,
    center: tuple[float, float],
    start_angle: float,
    end_angle: float,
    clockwise: bool,
) -> list[StrokeArc]:
    return [
        StrokeArc(
            line_id=line_id,
            center=center,
            radius=20.0,
            start_angle=start_angle,
            end_angle=end_angle,
            clockwise=clockwise,
            color="#000000",
            thickness=8.0,
            is_inactive=False,
        )
    ]


class StationTrackPointsTests(unittest.TestCase):
    def _junction_strokes(self) -> dict[str, list]:
        # two lines turning through the vertex from opposite sides, one
        # line running straight through it - the Donghu arrangement
        return {
            "A": _turning_line(
                "A",
                center=(80.0, 80.0),
                start_angle=math.pi / 2,
                end_angle=0.0,
                clockwise=True,
            ),
            "B": _turning_line(
                "B",
                center=(120.0, 120.0),
                start_angle=math.pi,
                end_angle=-math.pi / 2,
                clockwise=False,
            ),
            "C": [
                StrokeSegment(
                    line_id="C",
                    start=(80.0, 80.0),
                    end=(120.0, 120.0),
                    color="#000000",
                    thickness=8.0,
                    is_inactive=False,
                )
            ],
        }

    def test_reads_each_line_off_its_drawn_stroke(self) -> None:
        points = _station_track_points(
            (100, 100),
            ["A", "B", "C"],
            self._junction_strokes(),
            search_radius=48.0,
        )

        self.assertEqual(len(points), 3)
        offset = 20.0 - 20.0 * math.sqrt(0.5)
        self.assertAlmostEqual(points[0][0], 100.0 - offset, places=2)
        self.assertAlmostEqual(points[1][0], 100.0 + offset, places=2)
        self.assertEqual(points[2], (100.0, 100.0))

    def test_skips_lines_whose_stroke_is_out_of_range(self) -> None:
        strokes = self._junction_strokes()
        strokes["D"] = [
            StrokeSegment(
                line_id="D",
                start=(900.0, 900.0),
                end=(950.0, 900.0),
                color="#000000",
                thickness=8.0,
                is_inactive=False,
            )
        ]

        points = _station_track_points(
            (100, 100), ["A", "B", "C", "D"], strokes, search_radius=48.0
        )

        self.assertEqual(len(points), 3)

    def test_ignores_shared_track_overlays(self) -> None:
        strokes = self._junction_strokes()
        strokes["C"] = [
            StrokeSegment(
                line_id="C",
                start=(80.0, 80.0),
                end=(120.0, 120.0),
                color="#000000",
                thickness=4.0,
                is_inactive=False,
                is_overlay=True,
            )
        ]

        points = _station_track_points(
            (100, 100), ["A", "B", "C"], strokes, search_radius=48.0
        )

        self.assertEqual(len(points), 2)

    def test_junction_tracks_fit_a_diagonal_capsule(self) -> None:
        points = _station_track_points(
            (100, 100),
            ["A", "B", "C"],
            self._junction_strokes(),
            search_radius=48.0,
        )

        result = fit_junction_spread(
            (100.0, 100.0), points, tolerance=2.8, min_span=7.0
        )

        self.assertIsNotNone(result)
        assert result is not None
        axis, laterals = result
        self.assertAlmostEqual(abs(axis[0]), math.sqrt(0.5), places=3)
        self.assertAlmostEqual(abs(axis[1]), math.sqrt(0.5), places=3)

        symbol = build_station_symbol(
            (100, 100),
            is_transfer=True,
            normal=axis,
            laterals=laterals,
            styles=STYLES,
        )
        self.assertEqual(symbol.kind, "capsule")
        # every track centreline must sit on the capsule spine
        end_a = (
            symbol.pos[0] + symbol.normal[0] * symbol.lat_min,
            symbol.pos[1] + symbol.normal[1] * symbol.lat_min,
        )
        end_b = (
            symbol.pos[0] + symbol.normal[0] * symbol.lat_max,
            symbol.pos[1] + symbol.normal[1] * symbol.lat_max,
        )
        for point in points:
            dx, dy = end_b[0] - end_a[0], end_b[1] - end_a[1]
            t = ((point[0] - end_a[0]) * dx + (point[1] - end_a[1]) * dy) / (
                dx * dx + dy * dy
            )
            t = max(0.0, min(1.0, t))
            spine = (end_a[0] + t * dx, end_a[1] + t * dy)
            self.assertLessEqual(math.dist(point, spine), symbol.ring_radius)


if __name__ == "__main__":
    unittest.main()
