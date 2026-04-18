from __future__ import annotations

import os

from PIL import Image

from ..label_layout import place_label_block
from ..station_badges import collect_facility_tags, draw_badges, measure_badges
from ..station_labeling import (
    build_station_visual_state,
    measure_label_text,
    resolve_station_fonts,
)

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
_TOILET_INSIDE_PATH = os.path.join(_ASSETS_DIR, "toilet_inside.png")
_TOILET_OUTSIDE_PATH = os.path.join(_ASSETS_DIR, "toilet_outside.png")
TOILET_ICON_INSIDE: Image.Image | None = None
TOILET_ICON_OUTSIDE: Image.Image | None = None


def draw_stations(
    img,
    draw,
    stations: dict,
    lines: dict,
    get_pos,
    skip_map: set[tuple[str, str]],
    station_markers: dict[str, list[dict]],
    line_segments_for_collision: list[tuple[tuple[int, int], tuple[int, int]]],
    scale_factor: int,
    font_paths: list[str],
    styles: dict[str, float | str],
) -> None:
    global TOILET_ICON_INSIDE, TOILET_ICON_OUTSIDE
    if TOILET_ICON_INSIDE is None and os.path.exists(_TOILET_INSIDE_PATH):
        TOILET_ICON_INSIDE = Image.open(_TOILET_INSIDE_PATH).convert("RGBA")
    if TOILET_ICON_OUTSIDE is None and os.path.exists(_TOILET_OUTSIDE_PATH):
        TOILET_ICON_OUTSIDE = Image.open(_TOILET_OUTSIDE_PATH).convert("RGBA")

    label_boxes: list[tuple[float, float, float, float]] = []

    for s_id, s in stations.items():
        pos = get_pos(s_id)
        if not pos:
            continue

        visual_state = build_station_visual_state(s_id, s, lines, skip_map, styles)
        draw.ellipse(
            [
                pos[0] - visual_state.radius,
                pos[1] - visual_state.radius,
                pos[0] + visual_state.radius,
                pos[1] + visual_state.radius,
            ],
            fill="white",
            outline=visual_state.stroke_color,
            width=int(float(visual_state.stroke_width)),
        )

        facility_tags = collect_facility_tags(s)
        station_fonts = resolve_station_fonts(
            font_paths,
            styles,
            is_tram_station=visual_state.is_tram_station,
        )
        line_markers = station_markers.get(s_id, [])
        badge_metrics = measure_badges(
            draw,
            line_markers,
            facility_tags,
            font_paths,
            scale_factor,
        )
        text_metrics = measure_label_text(
            draw,
            s_id,
            s,
            station_fonts,
            scale_factor,
            badge_metrics.width,
            badge_metrics.height,
        )

        label_offset_base = float(styles["LABEL_OFFSET_BASE"])
        placement = place_label_block(
            pos,
            text_metrics.block_width,
            text_metrics.block_height,
            line_segments_for_collision,
            label_boxes,
            label_offset_base,
            scale_factor,
        )
        label_boxes.append(placement.box)
        bx = placement.x
        by = placement.y

        draw.text(
            (bx, by),
            text_metrics.name_cn,
            fill=visual_state.text_color_main,
            font=station_fonts.cn,
        )

        if text_metrics.name_en:
            draw.text(
                (bx, by + text_metrics.height_cn + text_metrics.gap),
                text_metrics.name_en,
                fill=visual_state.text_color_sub,
                font=station_fonts.en,
            )

        if line_markers or facility_tags:
            marker_start_x = bx + text_metrics.width_cn + float(4 * scale_factor)
            box_h = float(9 * scale_factor)
            inactive_color = str(styles["COLOR_INACTIVE"])
            cn_visual_center_y = (
                by + float(text_metrics.bbox_cn[1] + text_metrics.bbox_cn[3]) / 2
            )
            marker_y = cn_visual_center_y - box_h / 2
            draw_badges(
                draw,
                marker_start_x,
                marker_y,
                line_markers,
                facility_tags,
                font_paths,
                scale_factor,
                inactive_color,
            )
