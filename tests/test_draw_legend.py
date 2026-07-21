from __future__ import annotations

import unittest

from map_gen.draw.legend import draw_legend


class LegendDrawStub:
    def __init__(self) -> None:
        self.rectangle_calls: list[
            tuple[list[float], str | None, str | None, int | None]
        ] = []
        self.text_calls: list[tuple[tuple[float, float], str, str]] = []

    def textbbox(
        self,
        position: tuple[float, float],
        text: str,
        font: object | None = None,
    ) -> tuple[int, int, int, int]:
        _ = position, font
        return (0, 0, max(1, len(text)) * 8, 10)

    def rectangle(
        self,
        bounds: list[float],
        *,
        fill: str | None = None,
        outline: str | None = None,
        width: int | None = None,
    ) -> None:
        self.rectangle_calls.append((bounds, fill, outline, width))

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


class DrawLegendTests(unittest.TestCase):
    def test_draw_legend_renders_only_swatches_and_sorted_names(self) -> None:
        draw = LegendDrawStub()
        draw_legend(
            draw,
            {
                "B": {"name": {"zh-CN": "支线"}, "color": "#333333"},
                "2": {"name": {"zh-CN": "二号线"}, "color": "#00ff00"},
                "1": {"name": {"zh-CN": "一号线"}, "color": "#ff0000"},
                "10": {"name": {"zh-CN": "十号线"}, "color": "#cccccc"},
            },
            [],
            1,
            400,
            300,
            "#222222",
            "#dddddd",
        )

        # flat spec: no legend box, no header — one swatch per line only
        self.assertEqual(len(draw.rectangle_calls), 4)
        self.assertEqual(
            [call[1] for call in draw.rectangle_calls],
            ["#ff0000", "#00ff00", "#cccccc", "#333333"],
        )
        self.assertEqual(
            [call[1] for call in draw.text_calls],
            ["一号线", "二号线", "十号线", "支线"],
        )
        self.assertTrue(all(call[2] == "#222222" for call in draw.text_calls))


if __name__ == "__main__":
    unittest.main()
