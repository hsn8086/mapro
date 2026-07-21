from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from map_gen.renderer import draw_metro_map
from map_gen.svg_renderer import SvgCanvas, render_svg_string


class SvgRendererTests(unittest.TestCase):
    def test_svg_draw_text_keeps_pil_top_left_positioning(self) -> None:
        canvas = SvgCanvas(100, 100)
        font = canvas.draw._measure_draw.getfont()

        canvas.draw.text((12.5, 20.0), "11", fill="#ffffff", font=font)

        svg = canvas.to_svg()
        self.assertIn('x="12.5"', svg)
        self.assertIn('y="20"', svg)
        self.assertIn('dominant-baseline="text-before-edge"', svg)

    def test_render_svg_string_outputs_lines_stations_and_labels(self) -> None:
        svg = render_svg_string(
            {
                "meta": {
                    "name": {
                        "zh-CN": "测试线网图",
                        "en-US": "Test Network",
                    }
                },
                "stations": {
                    "a": {
                        "x": 0,
                        "y": 0,
                        "name": {"zh-CN": "甲站", "en-US": "Alpha"},
                    },
                    "b": {
                        "x": 50,
                        "y": 0,
                        "name": {"zh-CN": "乙站", "en-US": "Beta"},
                    },
                },
                "lines": {
                    "1": {
                        "id": "1",
                        "name": {"zh-CN": "一号线"},
                        "color": "#ff0000",
                        "stations": ["a", "b"],
                    }
                },
            }
        )

        self.assertIn("<svg", svg)
        self.assertIn("<path", svg)
        self.assertIn('stroke-linejoin="round"', svg)
        self.assertIn("<ellipse", svg)
        self.assertIn("甲站", svg)
        self.assertIn("ALPHA", svg)
        self.assertIn("测试线网图", svg)

    def test_draw_metro_map_writes_svg_for_svg_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "preview.svg"
            draw_metro_map(
                {
                    "stations": {
                        "a": {"x": 0, "y": 0, "name": {"zh-CN": "甲"}},
                        "b": {"x": 50, "y": 0, "name": {"zh-CN": "乙"}},
                    },
                    "lines": {
                        "1": {
                            "id": "1",
                            "color": "#ff0000",
                            "stations": ["a", "b"],
                        }
                    },
                },
                str(output_path),
            )

            self.assertTrue(output_path.exists())
            self.assertIn("<svg", output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
