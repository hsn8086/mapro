from __future__ import annotations

import os
from PIL import Image

from ..fonts import get_font
from ..label_layout import place_label_block
from ..station_badges import collect_facility_tags, draw_badges, measure_badges

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

    font_en = get_font(
        font_paths,
        int(float(styles["FONT_SIZE_LABEL_EN"])),
        priority_index=0,
        weight="Bold",
    )
    font_cn = get_font(
        font_paths,
        int(float(styles["FONT_SIZE_LABEL"])),
        priority_index=1,
        weight="Regular",
    )

    label_boxes: list[tuple[float, float, float, float]] = []

    for s_id, s in stations.items():
        pos = get_pos(s_id)
        if not pos:
            continue

        is_transfer = s.get("isTransfer", False)
        s_status = s.get("status", "active")

        fill_color = "white"
        stroke_color = str(styles["COLOR_STATION_STROKE"])

        if s_status != "active":
            stroke_color = str(styles["COLOR_INACTIVE"])

        active_stopping_lines: list[str] = []
        raw_lines = s.get("lines", [])
        for lid in raw_lines:
            if (lid, s_id) not in skip_map:
                active_stopping_lines.append(lid)

        if len(active_stopping_lines) >= 2:
            is_transfer = True
        elif len(active_stopping_lines) < 2 and is_transfer:
            is_transfer = False

        r = float(
            styles["STATION_RADIUS_TRANSFER"]
            if is_transfer
            else styles["STATION_RADIUS_NORMAL"]
        )
        stroke = float(
            styles["STATION_STROKE_TRANSFER"]
            if is_transfer
            else styles["STATION_STROKE"]
        )

        draw.ellipse(
            [pos[0] - r, pos[1] - r, pos[0] + r, pos[1] + r],
            fill=fill_color,
            outline=stroke_color,
            width=int(float(stroke)),
        )

        facility_tags = collect_facility_tags(s)

        name_cn = s.get("name", {}).get("zh-CN", s_id)
        name_en = s.get("name", {}).get("en-US", "").upper()

        text_color_main = str(styles["COLOR_TEXT_MAIN"])
        text_color_sub = str(styles["COLOR_TEXT_SUB"])

        if s_status != "active":
            text_color_main = str(styles["COLOR_INACTIVE"])
            text_color_sub = str(styles["COLOR_INACTIVE"])

        is_tram_station = False
        if active_stopping_lines:
            all_trams = True
            for lid in active_stopping_lines:
                l_type = lines.get(lid, {}).get("type", "subway")
                if l_type != "tram":
                    all_trams = False
                    break
            is_tram_station = all_trams

        current_font_cn = font_cn
        current_font_en = font_en
        if is_tram_station:
            current_font_cn = get_font(
                font_paths,
                int(float(styles["FONT_SIZE_LABEL"]) * 0.8),
                priority_index=1,
                weight="Bold",
            )
            current_font_en = get_font(
                font_paths,
                int(float(styles["FONT_SIZE_LABEL_EN"]) * 0.8),
                priority_index=0,
            )

        bbox_cn = draw.textbbox((0, 0), name_cn, font=current_font_cn)
        w_cn = float(bbox_cn[2] - bbox_cn[0])
        h_cn = float(bbox_cn[3] - bbox_cn[1])

        line_markers = station_markers.get(s_id, [])
        badge_metrics = measure_badges(
            draw,
            line_markers,
            facility_tags,
            font_paths,
            scale_factor,
        )
        w_markers = badge_metrics.width
        h_markers = badge_metrics.height

        if name_en:
            bbox_en = draw.textbbox((0, 0), name_en, font=current_font_en)
            w_en = float(bbox_en[2] - bbox_en[0])
            h_en = float(bbox_en[3] - bbox_en[1])
            gap = float(5 * scale_factor)
        else:
            w_en = 0.0
            h_en = 0.0
            gap = 0.0

        row1_w = float(w_cn + w_markers)
        block_w = float(max(row1_w, w_en))
        block_h = float(max(h_cn, h_markers) + gap + h_en)

        label_offset_base = float(styles["LABEL_OFFSET_BASE"])
        placement = place_label_block(
            pos,
            block_w,
            block_h,
            line_segments_for_collision,
            label_boxes,
            label_offset_base,
            scale_factor,
        )
        label_boxes.append(placement.box)
        bx = placement.x
        by = placement.y

        draw.text((bx, by), name_cn, fill=text_color_main, font=current_font_cn)

        if name_en:
            draw.text(
                (bx, by + h_cn + gap),
                name_en,
                fill=text_color_sub,
                font=current_font_en,
            )

        if line_markers or facility_tags:
            marker_start_x = bx + w_cn + float(4 * scale_factor)
            box_h = float(9 * scale_factor)
            inactive_color = str(styles["COLOR_INACTIVE"])

            cn_visual_center_y = by + float(bbox_cn[1] + bbox_cn[3]) / 2
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
