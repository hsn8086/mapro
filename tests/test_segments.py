from __future__ import annotations

import unittest

from map_gen.segments import build_segment_index, resolve_edge_shared_host


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

    def test_build_segment_index_keeps_injected_collinear_vertices(self) -> None:
        # B starts mid-way along A's straight run; the injected vertex must be
        # kept (no collinear compression) so the shared sub-segment is detected
        segment_data = build_segment_index(
            {
                "A": {"stations": ["a", "c"]},
                "B": {"stations": ["b", "c"]},
            },
            lambda station_id: {
                "a": (0, 0),
                "b": (10, 0),
                "c": (20, 0),
            }.get(station_id),
            lambda points: list(points),
        )

        self.assertEqual(
            segment_data.line_polylines["A"],
            [(0, 0), (10, 0), (20, 0)],
        )
        self.assertEqual(
            segment_data.segment_map[((10, 0), (20, 0))],
            ["A", "B"],
        )
        self.assertEqual(
            segment_data.segment_map[((0, 0), (10, 0))],
            ["A"],
        )

    def test_resolve_edge_shared_host_requires_both_ends_on_same_host(self) -> None:
        shared: list[str | None] = [None, "H", "H", None]

        self.assertIsNone(resolve_edge_shared_host(shared, 0))
        self.assertEqual(resolve_edge_shared_host(shared, 1), "H")
        self.assertIsNone(resolve_edge_shared_host(shared, 2))
        self.assertIsNone(resolve_edge_shared_host(shared, 3))

    def test_build_segment_index_drops_guest_from_shared_track_segments(self) -> None:
        # guest G declares shared track with host H on b-c: the guest keeps
        # its polyline but leaves the segment membership to the host
        segment_data = build_segment_index(
            {
                "H": {"stations": ["b", "c"]},
                "G": {
                    "stations": [
                        "a",
                        {"id": "b", "sharedTrack": "H"},
                        {"id": "c", "sharedTrack": "H"},
                    ]
                },
            },
            lambda station_id: {
                "a": (0, 0),
                "b": (10, 0),
                "c": (20, 0),
            }.get(station_id),
            lambda points: list(points),
        )

        self.assertEqual(segment_data.line_polylines["G"], [(0, 0), (10, 0), (20, 0)])
        self.assertEqual(segment_data.segment_map[((10, 0), (20, 0))], ["H"])
        self.assertEqual(segment_data.segment_map[((0, 0), (10, 0))], ["G"])
        self.assertEqual(segment_data.line_meta["G"]["shared"], [None, "H", "H"])

    def test_build_segment_index_keeps_guest_when_host_absent_from_segment(
        self,
    ) -> None:
        # sharedTrack pointing at a line that does not run there is ignored
        segment_data = build_segment_index(
            {
                "G": {
                    "stations": [
                        {"id": "b", "sharedTrack": "H"},
                        {"id": "c", "sharedTrack": "H"},
                    ]
                },
            },
            lambda station_id: {"b": (10, 0), "c": (20, 0)}.get(station_id),
            lambda points: list(points),
        )

        self.assertEqual(segment_data.segment_map[((10, 0), (20, 0))], ["G"])

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
