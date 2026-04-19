from __future__ import annotations

import unittest

from map_gen.layout import (
    calculate_station_bounds,
    expand_bounds,
    get_pos_transform,
    resolve_layout_bounds,
)


class LayoutBoundsTests(unittest.TestCase):
    def test_calculate_station_bounds_uses_station_coordinates(self) -> None:
        bounds = calculate_station_bounds(
            {
                "a": {"x": 10, "y": 30},
                "b": {"x": -5, "y": 7.5},
                "c": {"x": 18, "y": 0},
            }
        )

        self.assertEqual(bounds.min_x, -5.0)
        self.assertEqual(bounds.max_x, 18.0)
        self.assertEqual(bounds.min_y, 0.0)
        self.assertEqual(bounds.max_y, 30.0)

    def test_resolve_layout_bounds_prefers_explicit_viewport(self) -> None:
        bounds = resolve_layout_bounds(
            {"a": {"x": 10, "y": 20}},
            {"min_x": -100, "max_x": 100, "min_y": -50, "max_y": 50},
        )

        self.assertEqual(bounds.min_x, -100.0)
        self.assertEqual(bounds.max_x, 100.0)
        self.assertEqual(bounds.min_y, -50.0)
        self.assertEqual(bounds.max_y, 50.0)

    def test_resolve_layout_bounds_falls_back_when_viewport_incomplete(self) -> None:
        bounds = resolve_layout_bounds(
            {"a": {"x": 10, "y": 20}, "b": {"x": 30, "y": 40}},
            {"min_x": -100, "max_x": 100},
        )

        self.assertEqual(bounds.min_x, 10.0)
        self.assertEqual(bounds.max_x, 30.0)
        self.assertEqual(bounds.min_y, 20.0)
        self.assertEqual(bounds.max_y, 40.0)

    def test_expand_bounds_uses_span_based_margins(self) -> None:
        bounds = expand_bounds(
            calculate_station_bounds(
                {
                    "a": {"x": 100, "y": 200},
                    "b": {"x": 300, "y": 500},
                }
            ),
            min_margin=10,
            ratio=0.1,
        )

        self.assertEqual(bounds.min_x, 80.0)
        self.assertEqual(bounds.max_x, 320.0)
        self.assertEqual(bounds.min_y, 170.0)
        self.assertEqual(bounds.max_y, 530.0)

    def test_expand_bounds_prefers_tight_default_margins(self) -> None:
        bounds = expand_bounds(
            calculate_station_bounds(
                {
                    "a": {"x": 100, "y": 200},
                    "b": {"x": 300, "y": 500},
                }
            )
        )

        self.assertEqual(bounds.min_x, 92.0)
        self.assertEqual(bounds.max_x, 308.0)
        self.assertEqual(bounds.min_y, 192.0)
        self.assertEqual(bounds.max_y, 508.0)

    def test_get_pos_transform_uses_explicit_viewport_for_positioning(self) -> None:
        layout = get_pos_transform(
            {"a": {"x": 0, "y": 0}},
            viewport={"min_x": -100, "max_x": 100, "min_y": -50, "max_y": 50},
            scale_factor=1,
            padding=0,
        )

        self.assertEqual(layout.get_pos("a"), (100, 50))

    def test_get_pos_transform_expands_automatic_bounds_without_distorting_origin(
        self,
    ) -> None:
        layout = get_pos_transform(
            {"a": {"x": 100, "y": 200}, "b": {"x": 300, "y": 500}},
            scale_factor=1,
            padding=0,
        )

        self.assertEqual(layout.width, 216)
        self.assertEqual(layout.height, 316)
        self.assertEqual(layout.get_pos("a"), (8, 8))

    def test_get_pos_transform_adds_extra_top_padding(self) -> None:
        layout = get_pos_transform(
            {"a": {"x": 100, "y": 200}, "b": {"x": 300, "y": 500}},
            scale_factor=1,
            padding=0,
            extra_top_padding=40,
        )

        self.assertEqual(layout.width, 216)
        self.assertEqual(layout.height, 356)
        self.assertEqual(layout.get_pos("a"), (8, 48))

    def test_get_pos_transform_adds_extra_left_padding(self) -> None:
        layout = get_pos_transform(
            {"a": {"x": 100, "y": 200}, "b": {"x": 300, "y": 500}},
            scale_factor=1,
            padding=0,
            extra_left_padding=50,
        )

        self.assertEqual(layout.width, 266)
        self.assertEqual(layout.height, 316)
        self.assertEqual(layout.get_pos("a"), (58, 8))

    def test_get_pos_transform_adds_extra_bottom_padding(self) -> None:
        layout = get_pos_transform(
            {"a": {"x": 100, "y": 200}, "b": {"x": 300, "y": 500}},
            scale_factor=1,
            padding=0,
            extra_bottom_padding=60,
        )

        self.assertEqual(layout.width, 216)
        self.assertEqual(layout.height, 376)
        self.assertEqual(layout.get_pos("a"), (8, 8))


if __name__ == "__main__":
    unittest.main()
