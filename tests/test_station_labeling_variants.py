from __future__ import annotations

import unittest

from map_gen.station_labeling import measure_label_text, resolve_station_fonts


class DrawStub:
    def textbbox(
        self, _pos: tuple[int, int], text: str, font=None
    ) -> tuple[int, int, int, int]:
        _ = font
        return (0, 0, len(text) * 5, 8)


class StationLabelingVariantsTests(unittest.TestCase):
    def test_measure_label_text_returns_primary_and_compact_variants(self) -> None:
        draw = DrawStub()
        fonts = resolve_station_fonts(
            [],
            {"FONT_SIZE_LABEL": 13.0, "FONT_SIZE_LABEL_EN": 6.0},
            is_tram_station=False,
        )

        variant = measure_label_text(
            draw,
            "s1",
            {"name": {"zh-CN": "广州东站", "en-US": "Guangzhou East"}},
            fonts,
            scale_factor=1,
            badge_width=20.0,
            badge_height=9.0,
        )

        self.assertEqual(variant.primary.name_en, "GUANGZHOU EAST")
        self.assertEqual(variant.compact.name_en, "")
        self.assertGreater(variant.primary.block_height, variant.compact.block_height)
        self.assertGreaterEqual(
            variant.primary.block_width, variant.compact.block_width
        )
        self.assertIsNotNone(variant.primary.badges_y_offset)
        self.assertIsNotNone(variant.compact.badges_y_offset)

    def test_measure_label_text_compact_variant_respects_zero_badges(self) -> None:
        draw = DrawStub()
        fonts = resolve_station_fonts(
            [],
            {"FONT_SIZE_LABEL": 13.0, "FONT_SIZE_LABEL_EN": 6.0},
            is_tram_station=False,
        )

        variant = measure_label_text(
            draw,
            "s1",
            {"name": {"zh-CN": "公园前", "en-US": "Gongyuanqian"}},
            fonts,
            scale_factor=1,
            badge_width=0.0,
            badge_height=0.0,
        )

        self.assertEqual(variant.compact.block_width, variant.compact.width_cn)
        self.assertEqual(variant.compact.gap, 0.0)
        self.assertIsNone(variant.compact.english_y_offset)


if __name__ == "__main__":
    unittest.main()
