from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from map_gen.renderer import draw_metro_map
from map_gen.utils import prepare_canvas

SAMPLE_DATA = {
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
}


class PrepareCanvasTests(unittest.TestCase):
    def test_prepare_canvas_fills_requested_background_color(self) -> None:
        img, _ = prepare_canvas(4, 3, None, bg_color="#123456")

        self.assertEqual(img.size, (4, 3))
        self.assertEqual(img.getpixel((0, 0)), (0x12, 0x34, 0x56))


class DrawMetroMapTests(unittest.TestCase):
    def test_preview_max_edge_clamps_longest_output_edge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "preview.png"
            with contextlib.redirect_stdout(io.StringIO()):
                draw_metro_map(
                    SAMPLE_DATA,
                    str(output_path),
                    preview_max_edge=200,
                )

            with Image.open(output_path) as img:
                self.assertLessEqual(max(img.size), 200)

    def test_without_preview_max_edge_keeps_layout_size(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "preview.png"
            with contextlib.redirect_stdout(io.StringIO()):
                draw_metro_map(SAMPLE_DATA, str(output_path))

            with Image.open(output_path) as img:
                self.assertGreater(max(img.size), 200)


if __name__ == "__main__":
    unittest.main()
