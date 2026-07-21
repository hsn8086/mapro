from __future__ import annotations

import colorsys
import unittest

from map_gen.color_norm import normalize_line_color


def _hls_of(color: str) -> tuple[float, float, float]:
    text = color.lstrip("#")
    rgb = tuple(int(text[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    return colorsys.rgb_to_hls(*rgb)


class NormalizeLineColorTests(unittest.TestCase):
    def test_clamps_over_saturated_color_down(self) -> None:
        result = normalize_line_color("#ff0000")  # s = 1.0

        _, _, saturation = _hls_of(result)
        self.assertLessEqual(saturation, 0.85 + 0.01)
        self.assertGreaterEqual(saturation, 0.55 - 0.01)

    def test_clamps_lightness_into_band(self) -> None:
        light = normalize_line_color("#ffcccc")  # very light
        dark = normalize_line_color("#220000")  # very dark

        _, light_l, _ = _hls_of(light)
        _, dark_l, _ = _hls_of(dark)
        self.assertLessEqual(light_l, 0.58 + 0.01)
        self.assertGreaterEqual(dark_l, 0.38 - 0.01)

    def test_preserves_hue(self) -> None:
        for color in ("#ff0000", "#0044ff", "#00cc66", "#ffaa00"):
            with self.subTest(color=color):
                before_h, _, _ = _hls_of(color)
                after_h, _, _ = _hls_of(normalize_line_color(color))
                self.assertAlmostEqual(before_h, after_h, places=2)

    def test_color_already_in_band_is_unchanged(self) -> None:
        # h=0.6, l=0.5, s=0.7 sits inside both bands
        rgb = colorsys.hls_to_rgb(0.6, 0.5, 0.7)
        color = "#%02x%02x%02x" % tuple(round(c * 255) for c in rgb)

        self.assertEqual(normalize_line_color(color), color)

    def test_grey_returned_unchanged(self) -> None:
        self.assertEqual(normalize_line_color("#808080"), "#808080")
        self.assertEqual(normalize_line_color("#000000"), "#000000")
        self.assertEqual(normalize_line_color("#ffffff"), "#ffffff")

    def test_invalid_input_returned_unchanged(self) -> None:
        for value in ("", "not-a-color", "#12", "#12345", "#gggggg"):
            with self.subTest(value=value):
                self.assertEqual(normalize_line_color(value), value)

    def test_supports_three_digit_hex(self) -> None:
        self.assertEqual(
            normalize_line_color("#f00"),
            normalize_line_color("#ff0000"),
        )


if __name__ == "__main__":
    unittest.main()
