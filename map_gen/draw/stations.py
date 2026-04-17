from __future__ import annotations

import os
from PIL import Image

from ..fonts import get_font

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
_TOILET_INSIDE_PATH = os.path.join(_ASSETS_DIR, "toilet_inside.png")
_TOILET_OUTSIDE_PATH = os.path.join(_ASSETS_DIR, "toilet_outside.png")
TOILET_ICON_INSIDE: Image.Image | None = None
TOILET_ICON_OUTSIDE: Image.Image | None = None


def is_line_intersecting_rect(
    p1: tuple[int, int],
    p2: tuple[int, int],
    rect: tuple[float, float, float, float],
    padding: float = 0,
) -> bool:
    x1, y1 = p1
    x2, y2 = p2
    min_x, min_y, max_x, max_y = rect

    min_x -= padding
    min_y -= padding
    max_x += padding
    max_y += padding

    inside = 0
    left = 1
    right = 2
    bottom = 4
    top = 8

    def compute_out_code(x: float, y: float) -> int:
        code = inside
        if x < min_x:
            code |= left
        elif x > max_x:
            code |= right
        if y < min_y:
            code |= top
        elif y > max_y:
            code |= bottom
        return code

    code1 = compute_out_code(x1, y1)
    code2 = compute_out_code(x2, y2)

    while True:
        if not (code1 | code2):
            return True
        if code1 & code2:
            return False

        code_out = code1 if code1 else code2
        x = 0.0
        y = 0.0

        if code_out & top:
            x = x1 + (x2 - x1) * (min_y - y1) / (y2 - y1) if (y2 != y1) else x1
            y = min_y
        elif code_out & bottom:
            x = x1 + (x2 - x1) * (max_y - y1) / (y2 - y1) if (y2 != y1) else x1
            y = max_y
        elif code_out & right:
            y = y1 + (y2 - y1) * (max_x - x1) / (x2 - x1) if (x2 != x1) else y1
            x = max_x
        elif code_out & left:
            y = y1 + (y2 - y1) * (min_x - x1) / (x2 - x1) if (x2 != x1) else y1
            x = min_x

        if code_out == code1:
            x1, y1 = x, y
            code1 = compute_out_code(x1, y1)
        else:
            x2, y2 = x, y
            code2 = compute_out_code(x2, y2)


def is_box_colliding_with_lines(
    text_box: tuple[float, float, float, float],
    segments: list[tuple[tuple[int, int], tuple[int, int]]],
    threshold: float = 5,
) -> bool:
    for s1, s2 in segments:
        if is_line_intersecting_rect(s1, s2, text_box, padding=threshold):
            return True
    return False


def is_box_overlapping_other_labels(
    text_box: tuple[float, float, float, float],
    existing_boxes: list[tuple[float, float, float, float]],
    padding: float = 2,
) -> bool:
    t0x, t0y, t1x, t1y = text_box
    t0x -= padding
    t0y -= padding
    t1x += padding
    t1y += padding

    for e0x, e0y, e1x, e1y in existing_boxes:
        if not (t1x < e0x or t0x > e1x or t1y < e0y or t0y > e1y):
            return True
    return False


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

            for _tag in facility_tags:
                box_w_tag = float(12 * scale_factor)
                w_m_total += box_w_tag + float(2 * scale_factor)

            w_markers = float(w_m_total)

        if name_en:
            bbox_en = draw.textbbox((0, 0), name_en, font=current_font_en)
            w_en = float(bbox_en[2] - bbox_en[0])
            h_en = float(bbox_en[3] - bbox_en[1])
            gap = float(3 * scale_factor)
        else:
            w_en = 0.0
            h_en = 0.0
            gap = 0.0

        row1_w = float(w_cn + w_markers)
        block_w = float(max(row1_w, w_en))
        block_h = float(max(h_cn, h_markers) + gap + h_en)

        best_pos = None
        search_layers = [1.0, 1.3, 1.6]
        base_directions = [
            (1, 0),
            (1, 1),
            (1, -1),
            (0, -1),
            (0, 1),
            (-1, -1),
            (-1, 0),
            (-1, 1),
        ]

        found_safe_spot = False
        label_offset_base = float(styles["LABEL_OFFSET_BASE"])

        for layer_scale in search_layers:
            current_base = label_offset_base * layer_scale

            for dx, dy in base_directions:
                if dx != 0 and dy != 0:
                    ox = dx * current_base * 0.707 + (dx * block_w / 2 if dx < 0 else 0)
                    oy = dy * current_base * 0.707
                else:
                    ox = dx * current_base
                    oy = dy * current_base

                target_cx = pos[0] + dx * (current_base + block_w / 2)
                target_cy = pos[1] + dy * (current_base + block_h / 2)

                tx = target_cx - block_w / 2
                ty = target_cy - block_h / 2

                t_box = (tx, ty, tx + block_w, ty + block_h)

                if is_box_colliding_with_lines(
                    t_box,
                    line_segments_for_collision,
                    threshold=float(5 * scale_factor),
                ):
                    continue

                if is_box_overlapping_other_labels(
                    t_box, label_boxes, padding=float(1 * scale_factor)
                ):
                    continue

                best_pos = (tx, ty)
                label_boxes.append(t_box)
                found_safe_spot = True
                break

            if found_safe_spot:
                break

        if best_pos is None:
            fallback_dist = label_offset_base * 1.5
            tx = pos[0] + fallback_dist
            ty = pos[1] - fallback_dist
            best_pos = (tx, ty)
            label_boxes.append((tx, ty, tx + block_w, ty + block_h))

        bx, by = best_pos

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

            cn_visual_center_y = by + float(bbox_cn[1] + bbox_cn[3]) / 2
            marker_y = cn_visual_center_y - box_h / 2

            current_marker_x = marker_start_x

            for m_item in markers_list:
                m_color = m_item["color"]
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
                    (lid_tx_visual, lid_ty), lid_text, fill="white", font=font_marker_id
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

                box_stroke = max(1, int(scale_factor))
                icon_size = int(12 * scale_factor)
                icon_pad = float(2 * scale_factor)
                icon_box = float(icon_size + 2 * scale_factor)
                for tag in facility_tags:
                    is_outside = tag == "toilet_outside"
                    box_fill = "#f1f7ff" if is_outside else "#fff7ed"
                    box_outline = "#2563eb" if is_outside else "#f59e0b"
                    draw.rectangle(
                        [
                            current_marker_x,
                            marker_y,
                            current_marker_x + icon_box,
                            marker_y + box_h,
                        ],
                        fill=box_fill,
                        outline=box_outline,
                        width=box_stroke,
                    )

                    icon = TOILET_ICON_OUTSIDE if is_outside else TOILET_ICON_INSIDE
                    if icon:
                        icon_y = marker_y + (box_h - icon_size) / 2
                        icon_x = current_marker_x + icon_pad
                        icon_resized = icon.resize(
                            (icon_size, icon_size), Image.Resampling.LANCZOS
                        )
                        mask = icon_resized.split()[3]
                        icon_tint = Image.new(
                            "RGBA", (icon_size, icon_size), box_outline
                        )
                        icon_tint.putalpha(mask)
                        img.paste(
                            icon_tint,
                            (int(icon_x), int(icon_y)),
                            icon_tint,
                        )

                    current_marker_x += icon_box + float(2 * scale_factor)
