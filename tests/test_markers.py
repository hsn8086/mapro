from __future__ import annotations

import unittest

from map_gen.markers import build_station_markers


class StationMarkerTests(unittest.TestCase):
    def test_planned_station_marker_is_marked_inactive(self) -> None:
        markers = build_station_markers(
            {
                "1": {
                    "color": "#ff0000",
                    "stations": [
                        {"id": "s1", "num": "1"},
                        {"id": "s2", "num": "2", "status": "planned"},
                    ],
                }
            }
        )

        self.assertTrue(markers["s1"][0]["active"])
        self.assertFalse(markers["s2"][0]["active"])


if __name__ == "__main__":
    unittest.main()
