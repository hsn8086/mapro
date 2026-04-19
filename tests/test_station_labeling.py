from __future__ import annotations

import unittest

from map_gen.station_labeling import (
    build_station_visual_state,
    measure_label_text,
    resolve_station_fonts,
)


class DrawStub:
    def textbbox(
        self, _pos: tuple[int, int], text: str, font=None
    ) -> tuple[int, int, int, int]:
        _ = font
        return (0, 0, len(text) * 5, 8)


class StationLabelingTests(unittest.TestCase):
    def test_build_station_visual_state_resolves_transfer_and_tram_status(self) -> None:
        state = build_station_visual_state(
            "s1",
            {"isTransfer": False, "status": "active", "lines": ["T1", "T2"]},
            {"T1": {"type": "tram"}, "T2": {"type": "tram"}},
            set(),
            {
                "COLOR_STATION_STROKE": "#111111",
                "COLOR_TEXT_MAIN": "#222222",
                "COLOR_TEXT_SUB": "#333333",
                "COLOR_INACTIVE": "#cccccc",
                "STATION_RADIUS_NORMAL": 3.0,
                "STATION_RADIUS_TRANSFER": 6.0,
                "STATION_STROKE": 1.0,
                "STATION_STROKE_TRANSFER": 2.0,
            },
        )

        self.assertTrue(state.is_transfer)
        self.assertTrue(state.is_tram_station)
        self.assertEqual(state.radius, 6.0)
        self.assertEqual(state.stroke_width, 2.0)

    def test_build_station_visual_state_uses_inactive_colors(self) -> None:
        state = build_station_visual_state(
            "s1",
            {"status": "closed", "lines": ["1"]},
            {"1": {"type": "subway"}},
            set(),
            {
                "COLOR_STATION_STROKE": "#111111",
                "COLOR_TEXT_MAIN": "#222222",
                "COLOR_TEXT_SUB": "#333333",
                "COLOR_INACTIVE": "#cccccc",
                "COLOR_STATUS_PLANNED": "#bbbbbb",
                "COLOR_STATUS_UNDER_CONSTRUCTION": "#aa8844",
                "STATION_RADIUS_NORMAL": 3.0,
                "STATION_RADIUS_TRANSFER": 6.0,
                "STATION_STROKE": 1.0,
                "STATION_STROKE_TRANSFER": 2.0,
            },
        )

        self.assertEqual(state.stroke_color, "#cccccc")
        self.assertEqual(state.text_color_main, "#cccccc")
        self.assertEqual(state.text_color_sub, "#cccccc")

    def test_build_station_visual_state_uses_under_construction_colors(self) -> None:
        state = build_station_visual_state(
            "s1",
            {"status": "under_construction", "lines": ["1"]},
            {"1": {"type": "subway"}},
            set(),
            {
                "COLOR_STATION_STROKE": "#111111",
                "COLOR_TEXT_MAIN": "#222222",
                "COLOR_TEXT_SUB": "#333333",
                "COLOR_INACTIVE": "#cccccc",
                "COLOR_STATUS_PLANNED": "#bbbbbb",
                "COLOR_STATUS_UNDER_CONSTRUCTION": "#aa8844",
                "STATION_RADIUS_NORMAL": 3.0,
                "STATION_RADIUS_TRANSFER": 6.0,
                "STATION_STROKE": 1.0,
                "STATION_STROKE_TRANSFER": 2.0,
            },
        )

        self.assertEqual(state.stroke_color, "#aa8844")
        self.assertEqual(state.text_color_main, "#aa8844")
        self.assertEqual(state.text_color_sub, "#aa8844")

    def test_resolve_station_fonts_returns_font_pair(self) -> None:
        fonts = resolve_station_fonts(
            [],
            {"FONT_SIZE_LABEL": 13.0, "FONT_SIZE_LABEL_EN": 6.0},
            is_tram_station=False,
        )

        self.assertIsNotNone(fonts.cn)
        self.assertIsNotNone(fonts.en)

    def test_measure_label_text_combines_text_and_badge_metrics(self) -> None:
        draw = DrawStub()
        fonts = resolve_station_fonts(
            [],
            {"FONT_SIZE_LABEL": 13.0, "FONT_SIZE_LABEL_EN": 6.0},
            is_tram_station=False,
        )

        metrics = measure_label_text(
            draw,
            "s1",
            {"name": {"zh-CN": "广州东站", "en-US": "Guangzhou East"}},
            fonts,
            scale_factor=1,
            badge_width=20.0,
            badge_height=9.0,
        )
        primary = metrics.primary

        self.assertEqual(primary.name_cn, "广州东站")
        self.assertEqual(primary.name_en, "GUANGZHOU EAST")
        self.assertEqual(primary.width_cn, 20.0)
        self.assertEqual(primary.height_cn, 8.0)
        self.assertEqual(primary.width_en, 70.0)
        self.assertEqual(primary.height_en, 8.0)
        self.assertEqual(primary.gap, 4.0)
        self.assertEqual(primary.english_y_offset, 12.0)
        self.assertEqual(primary.badges_y_offset, 22.0)
        self.assertEqual(primary.block_width, 70.0)
        self.assertEqual(primary.block_height, 31.0)


if __name__ == "__main__":
    unittest.main()
