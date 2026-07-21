from __future__ import annotations

import unittest

from map_gen.draw.links import draw_transfer_connections


class LinkDrawStub:
    def __init__(self) -> None:
        self.line_calls: list[tuple[list[tuple[float, float]], str, int]] = []
        self.text_calls: list[tuple[tuple[float, float], str, str]] = []

    def line(
        self,
        points: list[tuple[float, float]],
        *,
        fill: str,
        width: int,
    ) -> None:
        self.line_calls.append((points, fill, width))

    def textbbox(
        self,
        position: tuple[float, float],
        text: str,
        font: object | None = None,
    ) -> tuple[int, int, int, int]:
        _ = position, font
        return (0, 0, max(1, len(text)) * 6, 8)

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


class DrawLinksTests(unittest.TestCase):
    def test_draw_transfer_connections_draws_physical_link_without_text(self) -> None:
        draw = LinkDrawStub()
        draw_transfer_connections(
            draw,
            [{"fromStationId": "a", "toStationId": "b", "type": "physical"}],
            lambda station_id: {"a": (10, 10), "b": (30, 10)}.get(station_id),
            1,
            [],
            {
                "FONT_SIZE_LABEL_EN": 6.0,
                "COLOR_CONNECTION_PHYSICAL": "#112233",
                "COLOR_CONNECTION_VIRTUAL": "#445566",
                "COLOR_CONNECTION_BUS": "#778899",
            },
        )

        self.assertEqual(draw.line_calls, [([(10, 10), (30, 10)], "#112233", 2)])
        # flat spec: connections carry no text annotations
        self.assertEqual(draw.text_calls, [])

    def test_draw_transfer_connections_draws_virtual_link_with_dashed_segments(
        self,
    ) -> None:
        draw = LinkDrawStub()
        draw_transfer_connections(
            draw,
            [{"fromStationId": "a", "toStationId": "b", "type": "virtual"}],
            lambda station_id: {"a": (10, 10), "b": (10, 40)}.get(station_id),
            1,
            [],
            {
                "FONT_SIZE_LABEL_EN": 6.0,
                "COLOR_CONNECTION_PHYSICAL": "#112233",
                "COLOR_CONNECTION_VIRTUAL": "#445566",
                "COLOR_CONNECTION_BUS": "#778899",
            },
        )

        self.assertGreater(len(draw.line_calls), 1)
        self.assertTrue(all(call[1] == "#445566" for call in draw.line_calls))
        self.assertEqual(draw.text_calls, [])


if __name__ == "__main__":
    unittest.main()
