from __future__ import annotations

import unittest

from map_gen.segments import build_segment_index


class SegmentIndexTests(unittest.TestCase):
    def test_build_segment_index_exposes_shared_segment_bundle_metadata(self) -> None:
        segment_data = build_segment_index(
            {
                "1": {"stations": ["a", "b"]},
                "2": {"stations": ["a", "b"]},
            },
            lambda station_id: {"a": (0, 0), "b": (10, 0)}.get(station_id),
            lambda points: list(points),
        )

        self.assertEqual(len(segment_data.shared_segments), 1)
        shared_segment = segment_data.shared_segments[0]
        self.assertEqual(shared_segment.start, (0, 0))
        self.assertEqual(shared_segment.end, (10, 0))
        self.assertEqual(shared_segment.line_ids, ("1", "2"))
        self.assertTrue(shared_segment.is_shared)
        self.assertEqual(segment_data.line_segments_for_collision, [((0, 0), (10, 0))])
        self.assertEqual(
            segment_data.tram_line_segments_for_collision,
            [],
        )

    def test_build_segment_index_keeps_single_line_segment_as_non_shared(self) -> None:
        segment_data = build_segment_index(
            {"1": {"stations": ["a", "b"]}},
            lambda station_id: {"a": (0, 0), "b": (10, 0)}.get(station_id),
            lambda points: list(points),
        )

        self.assertEqual(len(segment_data.shared_segments), 1)
        self.assertFalse(segment_data.shared_segments[0].is_shared)
        self.assertEqual(segment_data.shared_segments[0].line_ids, ("1",))

    def test_build_segment_index_collects_tram_segments_for_tram_collision_set(
        self,
    ) -> None:
        segment_data = build_segment_index(
            {
                "1": {"stations": ["a", "b"], "type": "subway"},
                "T1": {"stations": ["b", "c"], "type": "tram"},
            },
            lambda station_id: {"a": (0, 0), "b": (10, 0), "c": (20, 0)}.get(
                station_id
            ),
            lambda points: list(points),
        )

        self.assertEqual(
            segment_data.line_segments_for_collision,
            [((0, 0), (10, 0)), ((10, 0), (20, 0))],
        )
        self.assertEqual(
            segment_data.tram_line_segments_for_collision,
            [((10, 0), (20, 0))],
        )

    def test_build_segment_index_orders_bundle_by_local_continuity(self) -> None:
        segment_data = build_segment_index(
            {
                "A": {"stations": ["a", "b", "c", "d"]},
                "B": {"stations": ["e", "c", "d", "f"]},
            },
            lambda station_id: {
                "a": (0, 0),
                "b": (10, 10),
                "c": (20, 0),
                "d": (30, 0),
                "e": (20, -10),
                "f": (40, -10),
            }.get(station_id),
            lambda points: list(points),
        )

        shared_segment = next(
            segment
            for segment in segment_data.shared_segments
            if segment.key == ((20, 0), (30, 0))
        )
        self.assertEqual(shared_segment.line_ids, ("B", "A"))
        self.assertEqual(
            segment_data.segment_offsets[((20, 0), (30, 0))], {"B": 0, "A": 1}
        )


if __name__ == "__main__":
    unittest.main()
