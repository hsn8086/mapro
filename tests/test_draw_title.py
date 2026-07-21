from __future__ import annotations

import unittest

from map_gen.draw.title import draw_title_block


class TitleDrawStub:
    def __init__(self) -> None:
        self.text_calls: list[tuple[tuple[float, float], str, str]] = []

    def textbbox(
        self,
        position: tuple[float, float],
        text: str,
        font: object | None = None,
    ) -> tuple[int, int, int, int]:
        _ = position, font
        return (0, 0, max(1, len(text)) * 7, 12)

    def text(
        self,
        position: tuple[float, float],
        text: str,
        *,
        fill: str,
        font: object,
    ) -> None:
        _ = font
        self.text_calls.append((position, text, fill))


class DrawTitleTests(unittest.TestCase):
    def test_draw_title_block_draws_all_lines_in_order(self) -> None:
        draw = TitleDrawStub()
        bottom = draw_title_block(
            draw,
            {
                "name": {
                    "zh-CN": "广州地铁线网图",
                    "en-US": "Guangzhou Metro Map",
                },
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

        self.assertEqual(
            [call[1] for call in draw.text_calls],
            [
                "广州地铁线网图",
                "GUANGZHOU METRO MAP",
                "Designed by Mapro",
            ],
        )
        self.assertEqual(draw.text_calls[0][2], "#111111")
        self.assertEqual(draw.text_calls[1][2], "#666666")
        self.assertEqual(draw.text_calls[2][2], "#666666")
        self.assertEqual(bottom, draw.text_calls[-1][0][1] + 12)

    def test_draw_title_block_omits_meta_line_without_author(self) -> None:
        draw = TitleDrawStub()
        draw_title_block(
            draw,
            {
                "name": {
                    "zh-CN": "广州地铁线网图",
                    "en-US": "Guangzhou Metro Map",
                }
            },
            [],
            {
                "FONT_SIZE_TITLE": 32.0,
                "FONT_SIZE_SUBTITLE": 14.0,
                "COLOR_TEXT_MAIN": "#111111",
                "COLOR_TEXT_SUB": "#666666",
            },
        )

        self.assertEqual(
            [call[1] for call in draw.text_calls],
            ["广州地铁线网图", "GUANGZHOU METRO MAP"],
        )


if __name__ == "__main__":
    unittest.main()
