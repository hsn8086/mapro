from __future__ import annotations

import unittest

from PIL import Image, ImageDraw

from map_gen.draw.legend import measure_legend_block
from map_gen.draw.title import measure_title_block


class TitleLegendLayoutTests(unittest.TestCase):
    def test_measure_title_block_returns_positive_size(self) -> None:
        image = Image.new("RGB", (400, 300), "white")
        draw = ImageDraw.Draw(image)
        layout = measure_title_block(
            draw,
            {
                "name": {"zh-CN": "广州地铁线网图", "en-US": "Guangzhou Metro Map"},
                "author": "Mapro",
            },
            [],
            {
                "FONT_SIZE_TITLE": 32.0,
                "FONT_SIZE_SUBTITLE": 14.0,
                "COLOR_TEXT_MAIN": "#111111",
                "COLOR_TEXT_SUB": "#666666",
            },
        )

        self.assertGreater(layout.width, 0)
        self.assertGreater(layout.height, 0)
        self.assertGreaterEqual(layout.start_x, 0)
        self.assertGreaterEqual(layout.start_y, 0)
        self.assertEqual(len(layout.lines), 3)
        self.assertLess(layout.lines[0].y + layout.lines[0].bbox[3], layout.lines[1].y)
        self.assertLess(layout.lines[1].y + layout.lines[1].bbox[3], layout.lines[2].y)

    def test_measure_legend_block_uses_override_y(self) -> None:
        image = Image.new("RGB", (400, 300), "white")
        draw = ImageDraw.Draw(image)
        layout = measure_legend_block(
            draw,
            {
                "1": {"name": {"zh-CN": "一号线"}, "color": "#ff0000"},
                "2": {"name": {"zh-CN": "二号线"}, "color": "#00ff00"},
            },
            [],
            2,
            400,
            300,
            180.0,
        )

        self.assertEqual(layout.start_y, 180.0)
        self.assertGreater(layout.width, 0)
        self.assertGreater(layout.height, 0)

    def test_measure_legend_block_defaults_to_bottom_anchor(self) -> None:
        image = Image.new("RGB", (400, 300), "white")
        draw = ImageDraw.Draw(image)
        layout = measure_legend_block(
            draw,
            {
                "1": {"name": {"zh-CN": "一号线"}, "color": "#ff0000"},
            },
            [],
            2,
            400,
            300,
        )

        self.assertGreater(layout.start_y, 100.0)
        self.assertEqual(layout.start_y + layout.height + 40.0, 300.0)
