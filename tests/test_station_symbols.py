from __future__ import annotations

import unittest

from map_gen.draw.stations import _choose_station_axis
from map_gen.station_symbols import (
    build_station_symbol,
    find_station_axes,
    find_station_axis,
    render_station_symbol,
)

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
    def test_slot_renders_background_line_across_stroke(self) -> None:
        draw = SymbolDrawStub()
        symbol = build_station_symbol(
            (10, 10),
            is_transfer=False,
            normal=(0.0, 1.0),
            laterals=[0.0],
            styles=STYLES,
        )

        render_station_symbol(draw, symbol, STYLES)

        self.assertEqual(len(draw.line_calls), 1)
        self.assertEqual(draw.line_calls[0]["fill"], "#fafaf7")
        self.assertEqual(draw.ellipse_calls, [])
        self.assertEqual(draw.polygon_calls, [])

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


if __name__ == "__main__":
    unittest.main()
