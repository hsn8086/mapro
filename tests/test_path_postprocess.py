from __future__ import annotations

import unittest

from map_gen.path_postprocess import (
    build_corner_candidates,
    build_rounded_corner_geometry,
    classify_path_nodes,
    compress_collinear_points,
    postprocess_polyline,
)


class PathPostprocessTests(unittest.TestCase):
    def test_compress_collinear_points_removes_redundant_straight_points(self) -> None:
        self.assertEqual(
            compress_collinear_points([(0, 0), (5, 0), (10, 0), (15, 5)]),
            [(0, 0), (10, 0), (15, 5)],
        )

    def test_compress_collinear_points_preserves_turn_vertices(self) -> None:
        self.assertEqual(
            compress_collinear_points([(0, 0), (10, 0), (10, 10), (20, 20)]),
            [(0, 0), (10, 0), (10, 10), (20, 20)],
        )

    def test_postprocess_polyline_keeps_short_polylines_unchanged(self) -> None:
        self.assertEqual(postprocess_polyline([(0, 0), (10, 0)]), [(0, 0), (10, 0)])

    def test_classify_path_nodes_marks_start_corner_and_end(self) -> None:
        nodes = classify_path_nodes([(0, 0), (10, 0), (10, 10)])

        self.assertEqual([node.kind for node in nodes], ["start", "corner", "end"])
        self.assertFalse(nodes[0].is_turn)
        self.assertTrue(nodes[1].is_turn)
        self.assertEqual(nodes[1].turn_signature, ((1, 0), (0, 1)))
        self.assertEqual(nodes[2].dir_in, (0, 1))

    def test_classify_path_nodes_marks_inner_straight_node(self) -> None:
        nodes = classify_path_nodes([(0, 0), (10, 0), (20, 0), (20, 10)])

        self.assertEqual(
            [node.kind for node in nodes], ["start", "straight", "corner", "end"]
        )
        self.assertFalse(nodes[1].is_turn)
        self.assertEqual(nodes[1].dir_in, (1, 0))
        self.assertEqual(nodes[1].dir_out, (1, 0))

    def test_build_corner_candidates_limits_radius_by_line_width(self) -> None:
        candidates = build_corner_candidates(
            [(0, 0), (20, 0), (20, 20)],
            line_width=8.0,
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].point, (20, 0))
        self.assertEqual(candidates[0].segment_length_in, 20.0)
        self.assertEqual(candidates[0].segment_length_out, 20.0)
        self.assertAlmostEqual(candidates[0].turn_angle_radians, 1.57079632679)
        self.assertEqual(candidates[0].max_radius, 6.0)

    def test_build_corner_candidates_limits_radius_by_shorter_segment(self) -> None:
        candidates = build_corner_candidates(
            [(0, 0), (6, 0), (6, 20)],
            line_width=20.0,
        )

        self.assertEqual(len(candidates), 1)
        self.assertAlmostEqual(candidates[0].max_radius, 3.0)

    def test_build_corner_candidates_skips_zero_angle_reversal(self) -> None:
        candidates = build_corner_candidates(
            [(0, 0), (10, 0), (0, 0)],
            line_width=8.0,
        )

        self.assertEqual(candidates, ())

    def test_build_rounded_corner_geometry_returns_trimmed_arc_points(self) -> None:
        geometries = build_rounded_corner_geometry(
            [(0, 0), (20, 0), (20, 20)],
            line_width=8.0,
        )

        self.assertEqual(len(geometries), 1)
        geometry = geometries[0]
        self.assertEqual(geometry.corner_point, (20, 0))
        self.assertAlmostEqual(geometry.entry_point[0], 14.0)
        self.assertAlmostEqual(geometry.entry_point[1], 0.0)
        self.assertAlmostEqual(geometry.exit_point[0], 20.0)
        self.assertAlmostEqual(geometry.exit_point[1], 6.0)
        self.assertAlmostEqual(geometry.center_point[0], 14.0)
        self.assertAlmostEqual(geometry.center_point[1], 6.0)
        self.assertAlmostEqual(geometry.trim_distance, 6.0)
        self.assertFalse(geometry.clockwise)
