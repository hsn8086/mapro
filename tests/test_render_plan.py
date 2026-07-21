from __future__ import annotations

import unittest

from map_gen.color_norm import normalize_line_color
from map_gen.render_plan import build_render_plan


class RenderPlanTests(unittest.TestCase):
    def test_build_render_plan_collects_renderer_context(self) -> None:
        data = {
            "meta": {
                "name": {"zh-CN": "示例图"},
                "viewport": {"min_x": 0, "max_x": 100, "min_y": 0, "max_y": 50},
            },
            "stations": {
                "s1": {"x": 10, "y": 20, "name": {"zh-CN": "甲"}},
                "s2": {"x": 50, "y": 20, "name": {"zh-CN": "乙"}, "lines": ["1"]},
            },
            "lines": {
                "1": {
                    "id": "1",
                    "color": "#ff0000",
                    "stations": [
                        {"id": "s1", "num": "01"},
                        {"id": "s2", "num": "02", "status": "deferred"},
                    ],
                }
            },
            "connections": [
                {"fromStationId": "s1", "toStationId": "s2", "type": "physical"},
                "invalid-entry",
            ],
        }

        plan = build_render_plan(data, ["font-a.ttf"], badges_enabled=True)

        self.assertEqual(plan.meta["name"]["zh-CN"], "示例图")
        self.assertEqual(plan.font_paths, ["font-a.ttf"])
        self.assertEqual(plan.layout.width, 800)
        self.assertGreaterEqual(plan.layout.height, 700)
        s1_pos = plan.layout.get_pos("s1")
        self.assertIsNotNone(s1_pos)
        assert s1_pos is not None
        self.assertEqual(s1_pos[0], 320)
        self.assertGreaterEqual(s1_pos[1], 340)
        self.assertEqual(plan.connections, [data["connections"][0]])
        self.assertEqual(plan.line_width, float(plan.styles["LINE_WIDTH"]))
        self.assertIn("1", plan.segment_data.line_polylines)
        self.assertEqual(len(plan.segment_data.shared_segments), 1)
        self.assertIn(("1", "s2"), plan.segment_data.skip_map)
        self.assertTrue(plan.badges_enabled)
        self.assertIsInstance(plan.bundle_offsets, dict)
        self.assertEqual(plan.station_markers["s1"][0]["texts"], ["01"])
        self.assertFalse(plan.station_markers["s2"][0]["active"])
        # line colours are harmonised inside the plan
        self.assertEqual(plan.lines["1"]["color"], normalize_line_color("#ff0000"))

    def test_build_render_plan_disables_badges_by_default(self) -> None:
        plan = build_render_plan(
            {
                "stations": {
                    "s1": {"x": 0, "y": 0, "name": {"zh-CN": "甲"}},
                    "s2": {"x": 20, "y": 0, "name": {"zh-CN": "乙"}},
                },
                "lines": {
                    "1": {
                        "id": "1",
                        "color": "#ff0000",
                        "stations": [{"id": "s1", "num": "01"}, {"id": "s2"}],
                    }
                },
            }
        )

        self.assertFalse(plan.badges_enabled)
        self.assertEqual(plan.station_markers, {})

    def test_build_render_plan_uses_empty_defaults_for_invalid_sections(self) -> None:
        plan = build_render_plan(
            {
                "stations": {"s1": {"x": 0, "y": 0}},
                "lines": ["not-a-dict"],
                "meta": "invalid-meta",
                "connections": "invalid-connections",
            }
        )

        self.assertEqual(plan.lines, {})
        self.assertEqual(plan.meta, {})
        self.assertEqual(plan.connections, [])
        self.assertEqual(plan.station_markers, {})
        self.assertEqual(plan.segment_data.line_polylines, {})
        self.assertEqual(plan.font_paths, [])

    def test_build_render_plan_compresses_redundant_polyline_points(self) -> None:
        data = {
            "stations": {
                "s1": {"x": 0, "y": 0, "name": {"zh-CN": "甲"}},
                "s2": {"x": 20, "y": 0, "name": {"zh-CN": "乙"}},
                "s3": {"x": 40, "y": 0, "name": {"zh-CN": "丙"}},
            },
            "lines": {
                "1": {
                    "id": "1",
                    "color": "#ff0000",
                    "stations": ["s1", "s2", "s3"],
                }
            },
        }

        plan = build_render_plan(data)

        self.assertEqual(len(plan.segment_data.line_polylines["1"]), 2)


if __name__ == "__main__":
    unittest.main()
