from __future__ import annotations

import unittest

from map_gen.label_layout import (
    axis_direction_ranks,
    compute_leader_line,
    is_box_colliding_with_lines,
    is_box_overlapping_other_labels,
    is_line_intersecting_rect,
    place_label_block,
    slide_offsets,
)
from map_gen.label_context import LocalLabelContext, NearbyStation


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

    def test_place_label_block_prefers_right_side_over_other_safe_positions(
        self,
    ) -> None:
        placement = place_label_block(
            (100, 100),
            block_w=20.0,
            block_h=10.0,
            line_segments_for_collision=[],
            existing_boxes=[],
            label_offset_base=10.0,
            scale_factor=1,
        )

        self.assertEqual((placement.x, placement.y), (110.0, 95.0))

    def test_place_label_block_dodges_soft_segments_when_space_allows(self) -> None:
        # a planned line sits where the default spot would land: with free
        # space elsewhere the label must move off it
        placement = place_label_block(
            (100, 100),
            block_w=20.0,
            block_h=10.0,
            line_segments_for_collision=[],
            existing_boxes=[],
            label_offset_base=10.0,
            scale_factor=1,
            soft_line_segments=[((105, 95), (135, 95))],
        )

        self.assertNotEqual((placement.x, placement.y), (110.0, 95.0))

    def test_place_label_block_prefers_soft_hit_over_hard_line_hit(self) -> None:
        # every candidate collides with something: the winner must sit on
        # the planned (soft) line, not on the in-service (hard) line
        pos = (100, 100)
        hard: list[tuple[tuple[int, int], tuple[int, int]]] = []
        # in-service lines everywhere except to the left
        for offset in range(-80, 81, 8):
            hard.append(((100, 100 + offset), (220, 100 + offset)))
        soft = [((-60, 40), (99, 160))]
        placement = place_label_block(
            pos,
            block_w=20.0,
            block_h=10.0,
            line_segments_for_collision=hard,
            existing_boxes=[],
            label_offset_base=10.0,
            scale_factor=1,
            soft_line_segments=soft,
        )

        # label lands west of the station, in soft-line territory
        self.assertLess(placement.box[2], 101.0)

    def test_place_label_block_uses_nearer_safe_layer_when_multiple_exist(self) -> None:
        segments = [
            ((105, 95), (125, 95)),
            ((105, 85), (125, 85)),
        ]
        placement = place_label_block(
            (100, 100),
            block_w=20.0,
            block_h=10.0,
            line_segments_for_collision=segments,
            existing_boxes=[],
            label_offset_base=10.0,
            scale_factor=1,
        )

        # stays beside-right at the first layer (slid clear of the lines)
        # instead of jumping to a farther diagonal spot
        self.assertEqual(placement.x, 110.0)
        self.assertLess(placement.y, 110.0)
        self.assertFalse(
            is_box_colliding_with_lines(placement.box, segments, threshold=3.0)
        )

    def test_place_label_block_prefers_line_clear_candidate_when_all_overlap(
        self,
    ) -> None:
        context = LocalLabelContext(
            station_id="s1",
            dense=True,
            cluster_id=1,
            corridor_axis="none",
            corridor_index=0,
            preferred_directions=((0, 1), (1, 0)),
            tangent_vector=(0.0, 0.0),
            nearby_stations=(),
        )
        line_segments = [((125, 0), (125, 200))]
        existing_boxes = [(88.0, 108.0, 112.0, 128.0)]
        placement = place_label_block(
            (100, 100),
            block_w=20.0,
            block_h=10.0,
            line_segments_for_collision=line_segments,
            existing_boxes=existing_boxes,
            label_offset_base=10.0,
            scale_factor=1,
            local_context=context,
        )

        self.assertFalse(
            is_box_colliding_with_lines(placement.box, line_segments, threshold=5.0)
        )
        self.assertLessEqual(placement.box[3], existing_boxes[0][1])

    def test_place_label_block_prefers_overlap_clear_candidate_when_all_hit_lines(
        self,
    ) -> None:
        context = LocalLabelContext(
            station_id="s1",
            dense=True,
            cluster_id=1,
            corridor_axis="none",
            corridor_index=0,
            preferred_directions=((0, 1), (1, 0)),
            tangent_vector=(0.0, 0.0),
            nearby_stations=(),
        )
        line_segments = [((125, 0), (125, 200)), ((0, 125), (200, 125))]
        existing_boxes = [(88.0, 108.0, 112.0, 128.0)]
        placement = place_label_block(
            (100, 100),
            block_w=20.0,
            block_h=10.0,
            line_segments_for_collision=line_segments,
            existing_boxes=existing_boxes,
            label_offset_base=10.0,
            scale_factor=1,
            local_context=context,
        )

        self.assertFalse(
            is_box_overlapping_other_labels(placement.box, existing_boxes, padding=1.0)
        )
        self.assertLessEqual(placement.box[3], existing_boxes[0][1])

    def test_place_label_block_searches_farther_for_dense_safe_position(self) -> None:
        context = LocalLabelContext(
            station_id="s1",
            dense=True,
            cluster_id=1,
            corridor_axis="vertical",
            corridor_index=1,
            preferred_directions=((0, -1),),
            tangent_vector=(0.0, 1.0),
            nearby_stations=(),
        )

        obstacle = (90.0, 63.0, 110.0, 96.0)
        placement = place_label_block(
            (100, 100),
            block_w=20.0,
            block_h=10.0,
            line_segments_for_collision=[((0, 70), (200, 70))],
            existing_boxes=[obstacle],
            label_offset_base=10.0,
            scale_factor=1,
            local_context=context,
        )

        self.assertLess(placement.box[3], obstacle[1])

    def test_place_label_block_respects_dense_corridor_preferred_directions(
        self,
    ) -> None:
        context = LocalLabelContext(
            station_id="s1",
            dense=True,
            cluster_id=1,
            corridor_axis="vertical",
            corridor_index=1,
            preferred_directions=(
                (-1, 0),
                (-1, -1),
                (-1, 1),
                (0, -1),
                (0, 1),
                (1, 0),
                (1, 1),
                (1, -1),
            ),
            tangent_vector=(0.0, 1.0),
            nearby_stations=(
                NearbyStation("s0", (100, 60), False, 20.0, 10.0, False, 2),
                NearbyStation("s2", (100, 140), False, 20.0, 10.0, False, 2),
            ),
        )
        placement = place_label_block(
            (100, 100),
            block_w=20.0,
            block_h=10.0,
            line_segments_for_collision=[],
            existing_boxes=[],
            label_offset_base=10.0,
            scale_factor=1,
            local_context=context,
        )

        self.assertEqual((placement.x, placement.y), (70.0, 95.0))

    def test_is_box_colliding_with_lines_adds_segment_extents_to_padding(self) -> None:
        box = (10.0, 10.0, 20.0, 20.0)
        segment = ((0, 26), (30, 26))

        # 6 units away from the box: threshold 2 alone is not enough...
        self.assertFalse(is_box_colliding_with_lines(box, [segment], threshold=2.0))
        # ...but a wide bundle extent pushes the collision envelope out
        self.assertTrue(
            is_box_colliding_with_lines(
                box,
                [segment],
                threshold=2.0,
                segment_extents={segment: 5.0},
            )
        )

    def test_axis_direction_ranks_horizontal_prefers_below(self) -> None:
        ranks = axis_direction_ranks((1, 0))

        self.assertIsNotNone(ranks)
        assert ranks is not None
        self.assertEqual(ranks[0], (0, 1))

    def test_axis_direction_ranks_vertical_prefers_right(self) -> None:
        for axis in ((0, 1), (0, -1)):
            with self.subTest(axis=axis):
                ranks = axis_direction_ranks(axis)
                self.assertIsNotNone(ranks)
                assert ranks is not None
                self.assertEqual(ranks[0], (1, 0))

    def test_axis_direction_ranks_diagonal_prefers_clear_quadrant(self) -> None:
        down_right = axis_direction_ranks((1, 1))
        up_right = axis_direction_ranks((1, -1))

        assert down_right is not None and up_right is not None
        # first choices must be perpendicular-ish to the run, never along it
        self.assertNotIn(down_right[0], ((1, 1), (-1, -1)))
        self.assertNotIn(up_right[0], ((1, -1), (-1, 1)))

    def test_axis_direction_ranks_none_without_axis(self) -> None:
        self.assertIsNone(axis_direction_ranks(None))

    def test_place_label_block_follows_horizontal_axis_preference(self) -> None:
        placement = place_label_block(
            (100, 100),
            block_w=20.0,
            block_h=10.0,
            line_segments_for_collision=[],
            existing_boxes=[],
            label_offset_base=10.0,
            scale_factor=1,
            axis_dir=(1, 0),
        )

        # horizontal run: label sits below the station
        self.assertGreater(placement.box[1], 100.0)
        self.assertAlmostEqual((placement.box[0] + placement.box[2]) / 2, 100.0)

    def test_place_label_block_follows_vertical_axis_preference(self) -> None:
        placement = place_label_block(
            (100, 100),
            block_w=20.0,
            block_h=10.0,
            line_segments_for_collision=[],
            existing_boxes=[],
            label_offset_base=10.0,
            scale_factor=1,
            axis_dir=(0, 1),
        )

        # vertical run: label sits to the right of the station
        self.assertGreater(placement.box[0], 100.0)
        self.assertAlmostEqual((placement.box[1] + placement.box[3]) / 2, 100.0)

    def test_place_label_block_avoids_obstacle_boxes(self) -> None:
        obstacle = (105.0, 90.0, 135.0, 110.0)  # blocks the right side
        placement = place_label_block(
            (100, 100),
            block_w=20.0,
            block_h=10.0,
            line_segments_for_collision=[],
            existing_boxes=[],
            label_offset_base=10.0,
            scale_factor=1,
            obstacle_boxes=[obstacle],
        )

        self.assertFalse(
            is_box_overlapping_other_labels(placement.box, [obstacle], padding=0.0)
        )

    def test_slide_offsets_cardinal_directions_shift_perpendicular(self) -> None:
        # beside placements slide vertically, above/below slide horizontally
        for dx, dy in ((1, 0), (-1, 0)):
            for shift_x, shift_y in slide_offsets((dx, dy), 40.0, 20.0):
                self.assertEqual(shift_x, 0.0)
                self.assertNotEqual(shift_y, 0.0)
        for dx, dy in ((0, 1), (0, -1)):
            for shift_x, shift_y in slide_offsets((dx, dy), 40.0, 20.0):
                self.assertNotEqual(shift_x, 0.0)
                self.assertEqual(shift_y, 0.0)

    def test_slide_offsets_diagonal_directions_shift_either_axis(self) -> None:
        offsets = slide_offsets((1, 1), 40.0, 20.0)

        self.assertIn((-20.0, 0.0), offsets)
        self.assertIn((20.0, 0.0), offsets)
        self.assertIn((0.0, -10.0), offsets)
        self.assertIn((0.0, 10.0), offsets)
        self.assertNotIn((0.0, 0.0), offsets)

    def test_place_label_block_slides_into_tight_pocket_between_labels(self) -> None:
        # two label blocks flank a pocket beside the station that is barely
        # taller than the block: only a fine perpendicular slide fits; a
        # vertical line closes off the left side
        existing = [
            (105.0, 20.0, 200.0, 95.0),
            (105.0, 130.0, 200.0, 200.0),
        ]
        segments = [((55, -100), (55, 300))]
        placement = place_label_block(
            (100, 100),
            block_w=40.0,
            block_h=30.0,
            line_segments_for_collision=segments,
            existing_boxes=existing,
            label_offset_base=10.0,
            scale_factor=1,
        )

        # tucked beside-right, slid down into the free window
        self.assertEqual(placement.x, 110.0)
        self.assertGreater(placement.box[1], existing[0][3])
        self.assertLess(placement.box[3], existing[1][1])
        self.assertFalse(
            is_box_overlapping_other_labels(placement.box, existing, padding=1.0)
        )

    def test_compute_leader_line_returns_subtle_connector_for_far_label(self) -> None:
        leader = compute_leader_line((100, 100), (140.0, 80.0, 180.0, 110.0), 6.0, 1)

        self.assertIsNotNone(leader)
        assert leader is not None
        self.assertLess(leader[0][0], leader[1][0])
        self.assertLessEqual(leader[0][1], leader[1][1] + 20.0)


if __name__ == "__main__":
    unittest.main()
