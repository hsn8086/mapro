from __future__ import annotations

import unittest

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

        plan = build_render_plan(data, ["font-a.ttf"])

        self.assertEqual(plan.meta["name"]["zh-CN"], "示例图")
        self.assertEqual(plan.font_paths, ["font-a.ttf"])
        self.assertEqual(plan.layout.width, 800)
        self.assertEqual(plan.layout.height, 700)
        self.assertEqual(plan.layout.get_pos("s1"), (320, 340))
        self.assertEqual(plan.connections, [data["connections"][0]])
        self.assertEqual(plan.line_width, 18.0)
        self.assertIn("1", plan.segment_data.line_polylines)
        self.assertIn(("1", "s2"), plan.segment_data.skip_map)
        self.assertEqual(plan.station_markers["s1"][0]["texts"], ["01"])
        self.assertFalse(plan.station_markers["s2"][0]["active"])

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


if __name__ == "__main__":
    unittest.main()
