from __future__ import annotations

import unittest

from map_gen.label_context import StationContextInput, build_local_label_contexts


class LabelContextTests(unittest.TestCase):
    def test_build_local_label_contexts_detects_vertical_dense_cluster(self) -> None:
        contexts = build_local_label_contexts(
            [
                StationContextInput("a", (100, 100), 20.0, 10.0, False, False, 2),
                StationContextInput("b", (100, 145), 20.0, 10.0, True, False, 2),
                StationContextInput("c", (100, 190), 20.0, 10.0, False, False, 2),
            ],
            1,
        )

        self.assertTrue(contexts["a"].dense)
        self.assertEqual(contexts["a"].corridor_axis, "vertical")
        self.assertEqual(contexts["b"].corridor_axis, "vertical")
        self.assertEqual(len(contexts["a"].nearby_stations), 1)

    def test_build_local_label_contexts_prioritizes_transfer_station_in_cluster_order(
        self,
    ) -> None:
        contexts = build_local_label_contexts(
            [
                StationContextInput("a", (100, 100), 20.0, 10.0, False, False, 2),
                StationContextInput("b", (150, 100), 35.0, 12.0, True, True, 4),
                StationContextInput("c", (200, 100), 20.0, 10.0, False, False, 2),
            ],
            1,
        )

        self.assertEqual(contexts["b"].corridor_axis, "horizontal")
        self.assertEqual(contexts["b"].corridor_index, 0)

    def test_build_local_label_contexts_detects_tight_horizontal_pair(self) -> None:
        contexts = build_local_label_contexts(
            [
                StationContextInput("a", (100, 100), 20.0, 10.0, False, True, 2),
                StationContextInput("b", (150, 100), 28.0, 10.0, True, True, 2),
            ],
            1,
        )

        self.assertTrue(contexts["a"].dense)
        self.assertTrue(contexts["b"].dense)
        self.assertEqual(contexts["a"].corridor_axis, "horizontal")
        self.assertEqual(contexts["b"].corridor_axis, "horizontal")


if __name__ == "__main__":
    unittest.main()
