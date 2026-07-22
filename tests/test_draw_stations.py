from __future__ import annotations

import unittest
from unittest.mock import patch

from PIL import ImageFont

from map_gen.label_context import LocalLabelContext
from map_gen.label_layout import LabelPlacement
from map_gen.station_badges import BadgeMetrics, BadgeVariant
from map_gen.station_labeling import (
    LabelTextMetrics,
    LabelTextVariant,
    StationFonts,
    StationVisualState,
)
from map_gen.draw.stations import draw_stations


class StationDrawStub:
    def __init__(self) -> None:
        self.ellipse_calls: list[tuple[list[float], str, str, int]] = []
        self.line_calls: list[tuple[list[tuple[float, float]], str, int]] = []
        self.text_calls: list[tuple[tuple[float, float], str, str]] = []

    def ellipse(
        self,
        bounds: list[float],
        *,
        fill: str,
        outline: str,
        width: int,
    ) -> None:
        self.ellipse_calls.append((bounds, fill, outline, width))

    def line(
        self,
        points: list[tuple[float, float]],
        *,
        fill: str,
        width: int,
    ) -> None:
        self.line_calls.append((points, fill, width))

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


class DrawStationsTests(unittest.TestCase):
    def test_draw_stations_right_aligns_left_side_dense_label_block(self) -> None:
        draw = StationDrawStub()
        default_font = ImageFont.load_default()
        visual_state = StationVisualState(
            is_transfer=False,
            stroke_color="#123456",
            text_color_main="#111111",
            text_color_sub="#666666",
            radius=3.0,
            stroke_width=1.0,
            is_tram_station=False,
        )
        text_metrics = LabelTextMetrics(
            name_cn="东湖",
            name_en="DONGHU",
            bbox_cn=(0.0, 0.0, 20.0, 10.0),
            width_cn=20.0,
            height_cn=10.0,
            width_en=30.0,
            height_en=6.0,
            gap=4.0,
            badge_gap=2.0,
            badge_width=50.0,
            badge_height=8.0,
            english_y_offset=10.0,
            badges_y_offset=18.0,
            block_width=50.0,
            block_height=26.0,
        )
        text_variant = LabelTextVariant(primary=text_metrics, compact=text_metrics)
        badge_variant = BadgeVariant(
            primary=BadgeMetrics(width=50.0, height=8.0),
            compact=BadgeMetrics(width=0.0, height=0.0),
        )
        context = LocalLabelContext(
            station_id="s1",
            dense=True,
            cluster_id=1,
            corridor_axis="horizontal",
            corridor_index=0,
            preferred_directions=((0, -1), (0, 1)),
            tangent_vector=(1.0, 0.0),
            nearby_stations=(),
        )

        with (
            patch("map_gen.draw.stations.os.path.exists", return_value=False),
            patch(
                "map_gen.draw.stations.build_station_visual_state",
                return_value=visual_state,
            ),
            patch(
                "map_gen.draw.stations.collect_facility_tags",
                return_value=["toilet_inside"],
            ),
            patch(
                "map_gen.draw.stations.resolve_station_fonts",
                return_value=StationFonts(cn=default_font, en=default_font),
            ),
            patch(
                "map_gen.draw.stations.measure_badges",
                return_value=badge_variant,
            ),
            patch(
                "map_gen.draw.stations.measure_label_text",
                return_value=text_variant,
            ),
            patch(
                "map_gen.draw.stations.build_local_label_contexts",
                return_value={"s1": context},
            ),
            patch(
                "map_gen.draw.stations.place_label_block",
                return_value=LabelPlacement(
                    x=40.0,
                    y=30.0,
                    box=(40.0, 30.0, 90.0, 56.0),
                    score=0.0,
                ),
            ),
            patch(
                "map_gen.draw.stations.compute_leader_line",
                return_value=((96.0, 95.0), (90.0, 40.0)),
            ),
            patch("map_gen.draw.stations.draw_badges") as draw_badges_mock,
        ):
            draw_stations(
                None,
                draw,
                {"s1": {"name": {"zh-CN": "东湖", "en-US": "Donghu"}, "lines": ["1"]}},
                {"1": {"type": "subway"}},
                lambda station_id: (100, 100) if station_id == "s1" else None,
                set(),
                {
                    "s1": [
                        {
                            "line_id": "1",
                            "color": "#ff0000",
                            "texts": ["11"],
                            "active": True,
                        }
                    ]
                },
                [],
                [],
                1,
                [],
                {
                    "LINE_WIDTH": 8.0,
                    "LABEL_OFFSET_BASE": 10.0,
                    "COLOR_GUIDE_LINE": "#cccccc",
                    "COLOR_LEGEND_BORDER": "#bbbbbb",
                    "COLOR_INACTIVE": "#eeeeee",
                },
            )

        self.assertEqual(len(draw.ellipse_calls), 1)
        self.assertEqual(draw.ellipse_calls[0][2], "#123456")
        self.assertEqual(
            draw.line_calls, [([(96.0, 95.0), (90.0, 40.0)], "#cccccc", 1)]
        )
        self.assertEqual(draw.text_calls[0], ((70.0, 30.0), "东湖", "#111111"))
        self.assertEqual(draw.text_calls[1], ((60.0, 40.0), "DONGHU", "#666666"))
        assert draw_badges_mock.call_args is not None
        self.assertEqual(draw_badges_mock.call_args.args[1], 90.0)
        self.assertEqual(draw_badges_mock.call_args.args[2], 48.0)
        self.assertEqual(draw_badges_mock.call_args.kwargs["align"], "right")

    def test_draw_stations_uses_tram_only_collision_segments_for_tram_station(
        self,
    ) -> None:
        draw = StationDrawStub()
        default_font = ImageFont.load_default()
        visual_state = StationVisualState(
            is_transfer=False,
            stroke_color="#123456",
            text_color_main="#111111",
            text_color_sub="#666666",
            radius=3.0,
            stroke_width=1.0,
            is_tram_station=True,
        )
        text_metrics = LabelTextMetrics(
            name_cn="海傍",
            name_en="HAIBANG",
            bbox_cn=(0.0, 0.0, 20.0, 10.0),
            width_cn=20.0,
            height_cn=10.0,
            width_en=30.0,
            height_en=6.0,
            gap=4.0,
            badge_gap=2.0,
            badge_width=0.0,
            badge_height=0.0,
            english_y_offset=10.0,
            badges_y_offset=None,
            block_width=30.0,
            block_height=16.0,
        )
        text_variant = LabelTextVariant(primary=text_metrics, compact=text_metrics)
        badge_variant = BadgeVariant(
            primary=BadgeMetrics(width=0.0, height=0.0),
            compact=BadgeMetrics(width=0.0, height=0.0),
        )

        with (
            patch("map_gen.draw.stations.os.path.exists", return_value=False),
            patch(
                "map_gen.draw.stations.build_station_visual_state",
                return_value=visual_state,
            ),
            patch(
                "map_gen.draw.stations.collect_facility_tags",
                return_value=[],
            ),
            patch(
                "map_gen.draw.stations.resolve_station_fonts",
                return_value=StationFonts(cn=default_font, en=default_font),
            ),
            patch(
                "map_gen.draw.stations.measure_badges",
                return_value=badge_variant,
            ),
            patch(
                "map_gen.draw.stations.measure_label_text",
                return_value=text_variant,
            ),
            patch(
                "map_gen.draw.stations.build_local_label_contexts",
                return_value={"s1": None},
            ),
            patch(
                "map_gen.draw.stations.place_label_block",
                return_value=LabelPlacement(
                    x=110.0,
                    y=70.0,
                    box=(110.0, 70.0, 140.0, 86.0),
                    score=0.0,
                ),
            ) as place_label_block_mock,
        ):
            draw_stations(
                None,
                draw,
                {
                    "s1": {
                        "name": {"zh-CN": "海傍", "en-US": "Haibang"},
                        "lines": ["T1"],
                    }
                },
                {"T1": {"type": "tram"}},
                lambda station_id: (100, 100) if station_id == "s1" else None,
                set(),
                {},
                [((90, 90), (120, 90)), ((100, 100), (130, 100))],
                [((100, 100), (130, 100))],
                1,
                [],
                {
                    "LINE_WIDTH": 8.0,
                    "LABEL_OFFSET_BASE": 10.0,
                    "COLOR_GUIDE_LINE": "#cccccc",
                    "COLOR_LEGEND_BORDER": "#bbbbbb",
                    "COLOR_INACTIVE": "#eeeeee",
                },
            )

        self.assertEqual(
            place_label_block_mock.call_args.args[3],
            [((100, 100), (130, 100))],
        )

    def _make_simple_station_patches(
        self,
        *,
        facility_tags: list[str],
        placement_box: tuple[float, float, float, float] = (110.0, 70.0, 140.0, 86.0),
    ):
        default_font = ImageFont.load_default()
        visual_state = StationVisualState(
            is_transfer=False,
            stroke_color="#123456",
            text_color_main="#111111",
            text_color_sub="#666666",
            radius=3.0,
            stroke_width=1.0,
            is_tram_station=False,
        )
        text_metrics = LabelTextMetrics(
            name_cn="东湖",
            name_en="DONGHU",
            bbox_cn=(0.0, 0.0, 20.0, 10.0),
            width_cn=20.0,
            height_cn=10.0,
            width_en=30.0,
            height_en=6.0,
            gap=4.0,
            badge_gap=2.0,
            badge_width=0.0,
            badge_height=0.0,
            english_y_offset=10.0,
            badges_y_offset=None,
            block_width=30.0,
            block_height=16.0,
        )
        text_variant = LabelTextVariant(primary=text_metrics, compact=text_metrics)
        badge_variant = BadgeVariant(
            primary=BadgeMetrics(width=0.0, height=0.0),
            compact=BadgeMetrics(width=0.0, height=0.0),
        )
        return (
            patch("map_gen.draw.stations.os.path.exists", return_value=False),
            patch(
                "map_gen.draw.stations.build_station_visual_state",
                return_value=visual_state,
            ),
            patch(
                "map_gen.draw.stations.collect_facility_tags",
                return_value=facility_tags,
            ),
            patch(
                "map_gen.draw.stations.resolve_station_fonts",
                return_value=StationFonts(cn=default_font, en=default_font),
            ),
            patch(
                "map_gen.draw.stations.measure_badges",
                return_value=badge_variant,
            ),
            patch(
                "map_gen.draw.stations.measure_label_text",
                return_value=LabelTextVariant(
                    primary=text_metrics, compact=text_metrics
                ),
            ),
            patch(
                "map_gen.draw.stations.build_local_label_contexts",
                return_value={"s1": None},
            ),
            patch(
                "map_gen.draw.stations.place_label_block",
                return_value=LabelPlacement(
                    x=placement_box[0],
                    y=placement_box[1],
                    box=placement_box,
                    score=0.0,
                ),
            ),
        )

    def test_draw_stations_skips_facility_tags_when_badges_disabled(self) -> None:
        draw = StationDrawStub()
        patches = self._make_simple_station_patches(facility_tags=["toilet_inside"])
        with (
            patches[0],
            patches[1],
            patches[2] as collect_mock,
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patches[7],
        ):
            draw_stations(
                None,
                draw,
                {"s1": {"name": {"zh-CN": "东湖", "en-US": "Donghu"}, "lines": ["1"]}},
                {"1": {"type": "subway"}},
                lambda station_id: (100, 100) if station_id == "s1" else None,
                set(),
                {},
                [],
                [],
                1,
                [],
                {
                    "LINE_WIDTH": 8.0,
                    "LABEL_OFFSET_BASE": 10.0,
                    "COLOR_GUIDE_LINE": "#cccccc",
                    "COLOR_LEGEND_BORDER": "#bbbbbb",
                    "COLOR_INACTIVE": "#eeeeee",
                },
                badges_enabled=False,
            )

        collect_mock.assert_not_called()

    def test_draw_stations_renders_slot_symbol_when_axis_found(self) -> None:
        draw = StationDrawStub()
        patches = self._make_simple_station_patches(facility_tags=[])
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patches[7],
        ):
            draw_stations(
                None,
                draw,
                {"s1": {"name": {"zh-CN": "东湖", "en-US": "Donghu"}, "lines": ["1"]}},
                {"1": {"type": "subway"}},
                lambda station_id: (100, 100) if station_id == "s1" else None,
                set(),
                {},
                [],
                [],
                1,
                [],
                {
                    "LINE_WIDTH": 8.0,
                    "LABEL_OFFSET_BASE": 10.0,
                    "COLOR_GUIDE_LINE": "#cccccc",
                    "COLOR_LEGEND_BORDER": "#bbbbbb",
                    "COLOR_INACTIVE": "#eeeeee",
                    "COLOR_BG": "#ffffff",
                },
                line_polylines={"1": [(80, 100), (100, 100), (140, 100)]},
                segment_map={
                    ((80, 100), (100, 100)): ["1"],
                    ((100, 100), (140, 100)): ["1"],
                },
                bundle_offsets={},
            )

        # slot symbol renders as an inset background-coloured dot
        self.assertEqual(len(draw.ellipse_calls), 1)
        self.assertEqual(draw.ellipse_calls[0][1], "#ffffff")
        self.assertEqual(draw.line_calls, [])


if __name__ == "__main__":
    unittest.main()
