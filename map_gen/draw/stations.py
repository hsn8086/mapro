from __future__ import annotations

import os
from PIL import Image

from ..fonts import get_font
from ..label_layout import place_label_block

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

        facility_tags: list[str] = []
        for facility in s.get("facilities", []):
            if isinstance(facility, dict) and facility.get("type") == "toilet":
                desc = facility.get("description", {})
                location = None
                if isinstance(desc, dict):
                    location = desc.get("location")
                if location == "outside":
                    facility_tags.append("toilet_outside")
                else:
                    facility_tags.append("toilet_inside")
                break

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

        w_markers = 0.0
        h_markers = 0.0
        line_markers = station_markers.get(s_id, [])
        if line_markers or facility_tags:
            font_marker_dummy = get_font(
                font_paths, int(6 * scale_factor), weight="Bold"
            )
            box_h_dummy = 9 * scale_factor
            h_markers = float(box_h_dummy)
            w_m_total = float(4 * scale_factor)

            for m_item in line_markers:
                lid_text = str(m_item["line_id"])
                bbox_l = draw.textbbox((0, 0), lid_text, font=font_marker_dummy)
                w_l = float(bbox_l[2] - bbox_l[0])
                w_box = float(max(w_l + 3 * scale_factor, 10 * scale_factor))
                w_m_total += w_box

                for txt in m_item["texts"]:
                    bbox_t = draw.textbbox((0, 0), txt, font=font_marker_dummy)
                    w_t = float(bbox_t[2] - bbox_t[0])
                    w_m_total += float(2 * scale_factor) + w_t + float(3 * scale_factor)

                w_m_total += float(2 * scale_factor)

            if line_markers and facility_tags:
                w_m_total += float(2 * scale_factor)

            facility_font = get_font(font_paths, int(6 * scale_factor), weight="Bold")
            facility_label = "WC"
            facility_bbox = draw.textbbox((0, 0), facility_label, font=facility_font)
            facility_label_w = float(facility_bbox[2] - facility_bbox[0])

            for _tag in facility_tags:
                box_w_tag = float(facility_label_w + 2 * scale_factor)
                w_m_total += box_w_tag + float(2 * scale_factor)

            w_markers = float(w_m_total)

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
            markers_list = line_markers
            marker_start_x = bx + w_cn + float(4 * scale_factor)
            box_h = float(9 * scale_factor)
            font_marker_id = get_font(font_paths, int(6 * scale_factor), weight="Bold")
            font_marker_num = get_font(font_paths, int(6 * scale_factor), weight="Bold")
            inactive_color = str(styles["COLOR_INACTIVE"])

            cn_visual_center_y = by + float(bbox_cn[1] + bbox_cn[3]) / 2
            marker_y = cn_visual_center_y - box_h / 2

            current_marker_x = marker_start_x

            for m_item in markers_list:
                marker_is_active = bool(m_item.get("active", True))
                m_color = m_item["color"] if marker_is_active else inactive_color
                m_texts = m_item["texts"]

                lid_text = str(m_item["line_id"])
                bbox_lid = draw.textbbox((0, 0), lid_text, font=font_marker_id)
                w_lid = float(bbox_lid[2] - bbox_lid[0])
                box_w_lid = float(max(w_lid + 3 * scale_factor, 10 * scale_factor))

                draw.rectangle(
                    [
                        current_marker_x,
                        marker_y,
                        current_marker_x + box_w_lid,
                        marker_y + box_h,
                    ],
                    fill=m_color,
                )

                box_center_y = marker_y + box_h / 2
                lid_ty = box_center_y - float(bbox_lid[1] + bbox_lid[3]) / 2
                lid_tx_visual = (
                    current_marker_x
                    + box_w_lid / 2
                    - float(bbox_lid[0] + bbox_lid[2]) / 2
                )

                draw.text(
                    (lid_tx_visual, lid_ty),
                    lid_text,
                    fill="white",
                    font=font_marker_id,
                )

                current_marker_x += box_w_lid

                for txt in m_texts:
                    bbox_txt = draw.textbbox((0, 0), txt, font=font_marker_num)
                    w_txt = float(bbox_txt[2] - bbox_txt[0])

                    current_marker_x += float(2 * scale_factor)
                    txt_ty = box_center_y - float(bbox_txt[1] + bbox_txt[3]) / 2

                    draw.text(
                        (current_marker_x, txt_ty),
                        txt,
                        fill=m_color,
                        font=font_marker_num,
                    )

                    current_marker_x += w_txt + float(3 * scale_factor)

                current_marker_x += float(2 * scale_factor)

            if facility_tags:
                if markers_list:
                    current_marker_x += float(2 * scale_factor)

                facility_font = get_font(
                    font_paths, int(6 * scale_factor), weight="Bold"
                )
                facility_label = "WC"
                facility_bbox = draw.textbbox(
                    (0, 0), facility_label, font=facility_font
                )
                facility_label_w = float(facility_bbox[2] - facility_bbox[0])
                facility_box_w = float(facility_label_w + 2 * scale_factor)
                for tag in facility_tags:
                    is_outside = tag == "toilet_outside"
                    facility_color = "#2563eb" if is_outside else "#f59e0b"

                    facility_text_y = (
                        marker_y
                        + box_h / 2
                        - float(facility_bbox[1] + facility_bbox[3]) / 2
                    )
                    facility_text_x = current_marker_x + float(scale_factor)
                    draw.text(
                        (facility_text_x, facility_text_y),
                        facility_label,
                        fill=facility_color,
                        font=facility_font,
                    )

                    current_marker_x += facility_box_w + float(2 * scale_factor)
