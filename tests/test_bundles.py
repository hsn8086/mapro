from __future__ import annotations

import unittest

from map_gen.bundles import BundleChain, _detect_chains, build_bundle_offsets

Point = tuple[int, int]
SegmentKey = tuple[Point, Point]


def _segment_map_from(
    polylines: dict[str, list[Point]],
) -> dict[SegmentKey, list[str]]:
    segment_map: dict[SegmentKey, list[str]] = {}
    for line_id, polyline in polylines.items():
        for index in range(len(polyline) - 1):
            p1, p2 = polyline[index], polyline[index + 1]
            key = (p2, p1) if p1 > p2 else (p1, p2)
            segment_map.setdefault(key, []).append(line_id)
    return segment_map


class DetectChainsTests(unittest.TestCase):
    def test_detect_chains_finds_consecutive_shared_run(self) -> None:
        polylines = {
            "A": [(0, 0), (10, 0), (20, 0), (30, 0)],
            "B": [(0, 10), (10, 0), (20, 0), (30, 10)],
        }
        chains = _detect_chains(polylines, _segment_map_from(polylines))

        self.assertEqual(len(chains), 1)
        chain = chains[0]
        self.assertIsInstance(chain, BundleChain)
        self.assertEqual(chain.line_ids, ("A", "B"))
        self.assertEqual(chain.keys, (((10, 0), (20, 0)),))
        self.assertEqual(chain.vertices, ((10, 0), (20, 0)))

    def test_detect_chains_ignores_unshared_lines(self) -> None:
        polylines = {
            "A": [(0, 0), (10, 0)],
            "B": [(0, 10), (10, 10)],
        }
        chains = _detect_chains(polylines, _segment_map_from(polylines))

        self.assertEqual(chains, [])


class BuildBundleOffsetsTests(unittest.TestCase):
    def test_through_line_is_anchor_with_zero_offset(self) -> None:
        polylines = {
            "A": [(0, 0), (10, 0), (20, 0), (30, 0)],
            "B": [(0, 10), (10, 0), (20, 0), (30, 10)],
        }
        offsets = build_bundle_offsets(
            polylines,
            _segment_map_from(polylines),
            slot_spacing=10.0,
        )

        key = ((10, 0), (20, 0))
        # A keeps travelling straight past both chain ends -> anchor at 0
        self.assertEqual(offsets[("A", key)], 0.0)
        self.assertNotEqual(offsets[("B", key)], 0.0)

    def test_joining_line_stacks_on_its_approach_side(self) -> None:
        polylines = {
            "A": [(0, 0), (10, 0), (20, 0), (30, 0)],
            "B": [(0, 10), (10, 0), (20, 0), (30, 10)],
        }
        offsets = build_bundle_offsets(
            polylines,
            _segment_map_from(polylines),
            slot_spacing=10.0,
        )

        key = ((10, 0), (20, 0))
        # B approaches from +y; the canonical left normal of (1, 0) is (0, 1),
        # so a positive lateral keeps B on the side it came from
        self.assertEqual(offsets[("B", key)], 10.0)

    def test_reverse_traversal_keeps_canonical_sign(self) -> None:
        # same geometry, but both lines walk the shared run in -x direction:
        # the stored canonical-frame offsets must be identical
        polylines = {
            "A": [(30, 0), (20, 0), (10, 0), (0, 0)],
            "B": [(30, 10), (20, 0), (10, 0), (0, 10)],
        }
        offsets = build_bundle_offsets(
            polylines,
            _segment_map_from(polylines),
            slot_spacing=10.0,
        )

        key = ((10, 0), (20, 0))
        self.assertEqual(offsets[("A", key)], 0.0)
        self.assertEqual(offsets[("B", key)], 10.0)

    def test_two_joiners_from_opposite_sides_take_opposite_signs(self) -> None:
        polylines = {
            "A": [(0, 0), (10, 0), (20, 0), (30, 0)],
            "B": [(0, 10), (10, 0), (20, 0), (30, 10)],
            "C": [(0, -10), (10, 0), (20, 0), (30, -10)],
        }
        offsets = build_bundle_offsets(
            polylines,
            _segment_map_from(polylines),
            slot_spacing=10.0,
        )

        key = ((10, 0), (20, 0))
        self.assertEqual(offsets[("A", key)], 0.0)
        self.assertGreater(offsets[("B", key)], 0.0)
        self.assertLess(offsets[("C", key)], 0.0)

    def test_offsets_constant_along_multi_segment_chain(self) -> None:
        polylines = {
            "A": [(0, 0), (10, 0), (20, 0), (30, 0), (40, 0)],
            "B": [(0, 10), (10, 0), (20, 0), (30, 0), (40, 10)],
        }
        offsets = build_bundle_offsets(
            polylines,
            _segment_map_from(polylines),
            slot_spacing=10.0,
        )

        key_1 = ((10, 0), (20, 0))
        key_2 = ((20, 0), (30, 0))
        self.assertEqual(offsets[("A", key_1)], offsets[("A", key_2)])
        self.assertEqual(offsets[("B", key_1)], offsets[("B", key_2)])


if __name__ == "__main__":
    unittest.main()
