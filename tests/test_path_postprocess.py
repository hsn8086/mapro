from __future__ import annotations

import unittest

from map_gen.path_postprocess import compress_collinear_points, postprocess_polyline


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
