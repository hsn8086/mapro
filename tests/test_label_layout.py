from __future__ import annotations

import unittest

from map_gen.label_layout import (
    is_box_colliding_with_lines,
    is_box_overlapping_other_labels,
    is_line_intersecting_rect,
    place_label_block,
)


class LabelLayoutTests(unittest.TestCase):
    def test_is_line_intersecting_rect_detects_crossing_segment(self) -> None:
        self.assertTrue(
            is_line_intersecting_rect((0, 5), (10, 5), (3.0, 3.0, 7.0, 7.0))
        )
        self.assertFalse(
            is_line_intersecting_rect((0, 0), (2, 0), (3.0, 3.0, 7.0, 7.0))
        )

    def test_is_box_colliding_with_lines_uses_threshold(self) -> None:
        self.assertTrue(
            is_box_colliding_with_lines(
                (10.0, 10.0, 20.0, 20.0),
                [((0, 15), (8, 15))],
                threshold=2.5,
            )
        )
        self.assertFalse(
            is_box_colliding_with_lines(
                (10.0, 10.0, 20.0, 20.0),
                [((0, 15), (7, 15))],
                threshold=2.0,
            )
        )

    def test_is_box_overlapping_other_labels_respects_padding(self) -> None:
        existing = [(20.0, 20.0, 40.0, 40.0)]
        self.assertTrue(
            is_box_overlapping_other_labels(
                (40.5, 20.0, 50.0, 30.0), existing, padding=1.0
            )
        )
        self.assertFalse(
            is_box_overlapping_other_labels(
                (42.5, 20.0, 50.0, 30.0), existing, padding=1.0
            )
        )

    def test_place_label_block_picks_first_safe_direction(self) -> None:
        placement = place_label_block(
            (100, 100),
            block_w=20.0,
            block_h=10.0,
            line_segments_for_collision=[],
            existing_boxes=[],
            label_offset_base=10.0,
            scale_factor=1,
        )

        self.assertEqual(placement.x, 110.0)
        self.assertEqual(placement.y, 95.0)

    def test_place_label_block_skips_colliding_direction(self) -> None:
        placement = place_label_block(
            (100, 100),
            block_w=20.0,
            block_h=10.0,
            line_segments_for_collision=[((105, 95), (125, 95))],
            existing_boxes=[],
            label_offset_base=10.0,
            scale_factor=1,
        )

        self.assertNotEqual((placement.x, placement.y), (110.0, 95.0))


if __name__ == "__main__":
    unittest.main()
