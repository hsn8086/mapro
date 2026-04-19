from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageDraw

from .fonts import get_font


@dataclass(frozen=True)
class BadgeMetrics:
    width: float
    height: float


@dataclass(frozen=True)
class BadgeVariant:
    primary: BadgeMetrics
    compact: BadgeMetrics


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    stripped = color.lstrip("#")
    if len(stripped) != 6:
        return (52, 73, 94)
    return (int(stripped[0:2], 16), int(stripped[2:4], 16), int(stripped[4:6], 16))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _mix_with_white(color: str, strength: float) -> str:
    red, green, blue = _hex_to_rgb(color)
    mixed = (
        round(red + (255 - red) * strength),
        round(green + (255 - green) * strength),
        round(blue + (255 - blue) * strength),
    )
    return _rgb_to_hex(mixed)


def _draw_supersampled_pill(
    draw,
    bounds: tuple[float, float, float, float],
    *,
    fill: str,
    radius: int,
    text: str,
    text_fill: str,
    font_paths: list[str],
    font_size: int,
) -> None:
    if not hasattr(draw, "_image"):
        draw.rounded_rectangle(bounds, fill=fill, radius=radius)
        font = get_font(font_paths, font_size, weight="Bold")
        bbox = draw.textbbox((0, 0), text, font=font)
        center_x = (bounds[0] + bounds[2]) / 2
        center_y = (bounds[1] + bounds[3]) / 2
        text_x = center_x - float(bbox[0] + bbox[2]) / 2
        text_y = center_y - float(bbox[1] + bbox[3]) / 2
        draw.text((text_x, text_y), text, fill=text_fill, font=font)
        return

    scale = 4
    left, top, right, bottom = bounds
    width = max(1, int(round(right - left)))
    height = max(1, int(round(bottom - top)))
    layer = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
    layer_draw = ImageDraw.Draw(layer)
    layer_draw.rounded_rectangle(
        [0, 0, width * scale, height * scale],
        fill=fill,
        radius=radius * scale,
    )
    font = get_font(font_paths, font_size * scale, weight="Bold")
    bbox = layer_draw.textbbox((0, 0), text, font=font)
    center_x = width * scale / 2
    center_y = height * scale / 2
    text_x = center_x - float(bbox[0] + bbox[2]) / 2
    text_y = center_y - float(bbox[1] + bbox[3]) / 2
    layer_draw.text((text_x, text_y), text, fill=text_fill, font=font)

    resized = layer.resize((width, height), Image.Resampling.LANCZOS)
    draw._image.paste(resized, (int(round(left)), int(round(top))), resized)


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
) -> BadgeVariant:
    if not line_markers and not facility_tags:
        empty = BadgeMetrics(width=0.0, height=0.0)
        return BadgeVariant(primary=empty, compact=empty)

    font_marker = get_font(font_paths, int(5 * scale_factor), weight="Bold")
    badge_height = float(8 * scale_factor)
    total_width = 0.0
    marker_gap = float(3 * scale_factor)
    text_gap = float(2 * scale_factor)
    chip_padding = float(5 * scale_factor)
    line_box_min_width = float(11 * scale_factor)
    trailing_gap = float(2 * scale_factor)

    for index, marker in enumerate(line_markers):
        if index > 0:
            total_width += marker_gap

        line_text = str(marker["line_id"])
        line_bbox = draw.textbbox((0, 0), line_text, font=font_marker)
        line_width = float(line_bbox[2] - line_bbox[0])
        total_width += float(max(line_width + chip_padding, line_box_min_width))

        for text in marker["texts"]:
            text_bbox = draw.textbbox((0, 0), text, font=font_marker)
            text_width = float(text_bbox[2] - text_bbox[0])
            total_width += text_gap + text_width

    if facility_tags:
        if line_markers:
            total_width += marker_gap

        facility_label = "WC"
        facility_bbox = draw.textbbox((0, 0), facility_label, font=font_marker)
        facility_label_width = float(facility_bbox[2] - facility_bbox[0])
        facility_box_width = float(
            max(facility_label_width + chip_padding, 10 * scale_factor)
        )
        for index, _tag in enumerate(facility_tags):
            if index > 0:
                total_width += marker_gap
            total_width += facility_box_width

    if line_markers or facility_tags:
        total_width += trailing_gap

    primary = BadgeMetrics(width=total_width, height=badge_height)
    compact = BadgeMetrics(width=0.0, height=0.0)
    return BadgeVariant(primary=primary, compact=compact)


def draw_badges(
    draw,
    start_x: float,
    marker_y: float,
    line_markers: list[dict[str, Any]],
    facility_tags: list[str],
    font_paths: list[str],
    scale_factor: int,
    inactive_color: str,
    align: str = "left",
) -> None:
    if not line_markers and not facility_tags:
        return

    box_height = float(8 * scale_factor)
    line_radius = max(1, int(2 * scale_factor))
    facility_radius = line_radius
    font_marker_id = get_font(font_paths, int(5 * scale_factor), weight="Bold")
    font_marker_num = get_font(font_paths, int(5 * scale_factor), weight="Bold")
    current_x = start_x
    marker_gap = float(3 * scale_factor)
    text_gap = float(2 * scale_factor)
    chip_padding = float(5 * scale_factor)
    line_box_min_width = float(11 * scale_factor)
    trailing_gap = float(2 * scale_factor)

    total_variant = measure_badges(
        draw, line_markers, facility_tags, font_paths, scale_factor
    )
    total_width = total_variant.primary.width
    if align == "right":
        current_x = start_x - total_width

    for index, marker in enumerate(line_markers):
        if index > 0:
            current_x += marker_gap

        marker_is_active = bool(marker.get("active", True))
        marker_color = str(marker["color"]) if marker_is_active else inactive_color
        marker_texts = marker["texts"]

        line_text = str(marker["line_id"])
        line_bbox = draw.textbbox((0, 0), line_text, font=font_marker_id)
        line_width = float(line_bbox[2] - line_bbox[0])
        line_box_width = float(max(line_width + chip_padding, line_box_min_width))

        line_bounds = (
            current_x,
            marker_y,
            current_x + line_box_width,
            marker_y + box_height,
        )
        _draw_supersampled_pill(
            draw,
            line_bounds,
            fill=marker_color,
            radius=line_radius,
            text=line_text,
            text_fill="white",
            font_paths=font_paths,
            font_size=int(5 * scale_factor),
        )

        box_center_y = marker_y + box_height / 2
        current_x += line_box_width

        for text in marker_texts:
            text_bbox = draw.textbbox((0, 0), text, font=font_marker_num)
            text_width = float(text_bbox[2] - text_bbox[0])

            current_x += text_gap
            text_y = box_center_y - float(text_bbox[1] + text_bbox[3]) / 2
            draw.text(
                (current_x, text_y),
                text,
                fill=marker_color,
                font=font_marker_num,
            )
            current_x += text_width

    if facility_tags:
        if line_markers:
            current_x += marker_gap

        facility_font = get_font(font_paths, int(5 * scale_factor), weight="Bold")
        facility_label = "WC"
        facility_bbox = draw.textbbox((0, 0), facility_label, font=facility_font)
        facility_label_width = float(facility_bbox[2] - facility_bbox[0])
        facility_box_width = float(
            max(facility_label_width + chip_padding, 10 * scale_factor)
        )
        for index, tag in enumerate(facility_tags):
            if index > 0:
                current_x += marker_gap
            is_outside = tag == "toilet_outside"
            facility_color = "#2563eb" if is_outside else "#c97a00"
            facility_bg = "#e8f1ff" if is_outside else "#fff2df"
            facility_bounds = (
                current_x,
                marker_y,
                current_x + facility_box_width,
                marker_y + box_height,
            )
            _draw_supersampled_pill(
                draw,
                facility_bounds,
                fill=facility_bg,
                radius=facility_radius,
                text=facility_label,
                text_fill=facility_color,
                font_paths=font_paths,
                font_size=int(5 * scale_factor),
            )
            current_x += facility_box_width

    if line_markers or facility_tags:
        current_x += trailing_gap
