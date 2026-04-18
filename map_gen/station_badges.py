from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .fonts import get_font


@dataclass(frozen=True)
class BadgeMetrics:
    width: float
    height: float


def collect_facility_tags(station: dict[str, Any]) -> list[str]:
    facility_tags: list[str] = []
    for facility in station.get("facilities", []):
        if isinstance(facility, dict) and facility.get("type") == "toilet":
            description = facility.get("description", {})
            location = (
                description.get("location") if isinstance(description, dict) else None
            )
            facility_tags.append(
                "toilet_outside" if location == "outside" else "toilet_inside"
            )
            break
    return facility_tags


def measure_badges(
    draw,
    line_markers: list[dict[str, Any]],
    facility_tags: list[str],
    font_paths: list[str],
    scale_factor: int,
) -> BadgeMetrics:
    if not line_markers and not facility_tags:
        return BadgeMetrics(width=0.0, height=0.0)

    font_marker = get_font(font_paths, int(6 * scale_factor), weight="Bold")
    badge_height = float(9 * scale_factor)
    total_width = float(4 * scale_factor)

    for marker in line_markers:
        line_text = str(marker["line_id"])
        line_bbox = draw.textbbox((0, 0), line_text, font=font_marker)
        line_width = float(line_bbox[2] - line_bbox[0])
        total_width += float(max(line_width + 3 * scale_factor, 10 * scale_factor))

        for text in marker["texts"]:
            text_bbox = draw.textbbox((0, 0), text, font=font_marker)
            text_width = float(text_bbox[2] - text_bbox[0])
            total_width += (
                float(2 * scale_factor) + text_width + float(3 * scale_factor)
            )

        total_width += float(2 * scale_factor)

    if line_markers and facility_tags:
        total_width += float(2 * scale_factor)

    if facility_tags:
        facility_label = "WC"
        facility_bbox = draw.textbbox((0, 0), facility_label, font=font_marker)
        facility_label_width = float(facility_bbox[2] - facility_bbox[0])
        facility_box_width = float(facility_label_width + 2 * scale_factor)
        for _tag in facility_tags:
            total_width += facility_box_width + float(2 * scale_factor)

    return BadgeMetrics(width=total_width, height=badge_height)


def draw_badges(
    draw,
    start_x: float,
    marker_y: float,
    line_markers: list[dict[str, Any]],
    facility_tags: list[str],
    font_paths: list[str],
    scale_factor: int,
    inactive_color: str,
) -> None:
    if not line_markers and not facility_tags:
        return

    box_height = float(9 * scale_factor)
    font_marker_id = get_font(font_paths, int(6 * scale_factor), weight="Bold")
    font_marker_num = get_font(font_paths, int(6 * scale_factor), weight="Bold")
    current_x = start_x

    for marker in line_markers:
        marker_is_active = bool(marker.get("active", True))
        marker_color = str(marker["color"]) if marker_is_active else inactive_color
        marker_texts = marker["texts"]

        line_text = str(marker["line_id"])
        line_bbox = draw.textbbox((0, 0), line_text, font=font_marker_id)
        line_width = float(line_bbox[2] - line_bbox[0])
        line_box_width = float(max(line_width + 3 * scale_factor, 10 * scale_factor))

        draw.rectangle(
            [current_x, marker_y, current_x + line_box_width, marker_y + box_height],
            fill=marker_color,
        )

        box_center_y = marker_y + box_height / 2
        line_text_y = box_center_y - float(line_bbox[1] + line_bbox[3]) / 2
        line_text_x = (
            current_x + line_box_width / 2 - float(line_bbox[0] + line_bbox[2]) / 2
        )
        draw.text(
            (line_text_x, line_text_y), line_text, fill="white", font=font_marker_id
        )

        current_x += line_box_width

        for text in marker_texts:
            text_bbox = draw.textbbox((0, 0), text, font=font_marker_num)
            text_width = float(text_bbox[2] - text_bbox[0])

            current_x += float(2 * scale_factor)
            text_y = box_center_y - float(text_bbox[1] + text_bbox[3]) / 2
            draw.text(
                (current_x, text_y), text, fill=marker_color, font=font_marker_num
            )
            current_x += text_width + float(3 * scale_factor)

        current_x += float(2 * scale_factor)

    if facility_tags:
        if line_markers:
            current_x += float(2 * scale_factor)

        facility_font = get_font(font_paths, int(6 * scale_factor), weight="Bold")
        facility_label = "WC"
        facility_bbox = draw.textbbox((0, 0), facility_label, font=facility_font)
        facility_label_width = float(facility_bbox[2] - facility_bbox[0])
        facility_box_width = float(facility_label_width + 2 * scale_factor)
        for tag in facility_tags:
            is_outside = tag == "toilet_outside"
            facility_color = "#2563eb" if is_outside else "#f59e0b"
            facility_text_y = (
                marker_y
                + box_height / 2
                - float(facility_bbox[1] + facility_bbox[3]) / 2
            )
            facility_text_x = current_x + float(scale_factor)
            draw.text(
                (facility_text_x, facility_text_y),
                facility_label,
                fill=facility_color,
                font=facility_font,
            )
            current_x += facility_box_width + float(2 * scale_factor)
