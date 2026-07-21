from __future__ import annotations

import unittest
from unittest.mock import patch

from map_gen.render_pipeline import draw_render_plan
from map_gen.render_plan import build_render_plan


class RenderPipelineTests(unittest.TestCase):
    def test_draw_render_plan_invokes_shared_draw_steps(self) -> None:
        plan = build_render_plan(
            {
                "stations": {
                    "a": {"x": 0, "y": 0, "name": {"zh-CN": "甲"}},
                    "b": {"x": 20, "y": 0, "name": {"zh-CN": "乙"}},
                },
                "lines": {"1": {"id": "1", "color": "#f00", "stations": ["a", "b"]}},
            }
        )

        with (
            patch("map_gen.render_pipeline.draw_lines") as draw_lines_mock,
            patch("map_gen.render_pipeline.draw_transfer_connections") as links_mock,
            patch("map_gen.render_pipeline.draw_stations") as stations_mock,
            patch("map_gen.render_pipeline.draw_title_block") as title_mock,
            patch("map_gen.render_pipeline.draw_legend") as legend_mock,
        ):
            draw_render_plan(plan, object(), object())

        draw_lines_mock.assert_called_once()
        links_mock.assert_called_once()
        stations_mock.assert_called_once()
        title_mock.assert_called_once()
        legend_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
