from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PIL import ImageFont

from .fonts import get_font
from .styles import resolve_status_color


@dataclass(frozen=True)
class StationVisualState:
    is_transfer: bool
    stroke_color: str
    text_color_main: str
    text_color_sub: str
    radius: float
    stroke_width: float
    is_tram_station: bool


@dataclass(frozen=True)
class StationFonts:
    cn: ImageFont.FreeTypeFont | ImageFont.ImageFont
    en: ImageFont.FreeTypeFont | ImageFont.ImageFont


@dataclass(frozen=True)
class LabelTextMetrics:
    name_cn: str
    name_en: str
    bbox_cn: tuple[float, float, float, float]
    width_cn: float
    height_cn: float
    width_en: float
    height_en: float
    gap: float
    badge_gap: float
    badge_width: float
    badge_height: float
    english_y_offset: float | None
    badges_y_offset: float | None
    block_width: float
    block_height: float


@dataclass(frozen=True)
class LabelTextVariant:
    primary: LabelTextMetrics
    compact: LabelTextMetrics


def build_station_visual_state(
    station_id: str,
    station: dict[str, Any],
    lines: dict[str, Any],
    skip_map: set[tuple[str, str]],
    styles: dict[str, float | str],
) -> StationVisualState:
    is_transfer = bool(station.get("isTransfer", False))
    station_status = str(station.get("status", "active"))
    active_stopping_lines: list[str] = []

    raw_lines = station.get("lines", [])
    if isinstance(raw_lines, list):
        for line_id in raw_lines:
            if isinstance(line_id, str) and (line_id, station_id) not in skip_map:
                active_stopping_lines.append(line_id)

    if len(active_stopping_lines) >= 2:
        is_transfer = True
    elif len(active_stopping_lines) < 2 and is_transfer:
        is_transfer = False

    stroke_color = str(styles["COLOR_STATION_STROKE"])
    text_color_main = str(styles["COLOR_TEXT_MAIN"])
    text_color_sub = str(styles["COLOR_TEXT_SUB"])
    if station_status != "active":
        stroke_color = resolve_status_color(
            station_status,
            styles,
            active_color=stroke_color,
        )
        text_color_main = resolve_status_color(
            station_status,
            styles,
            active_color=text_color_main,
        )
        text_color_sub = resolve_status_color(
            station_status,
            styles,
            active_color=text_color_sub,
        )

    is_tram_station = bool(active_stopping_lines) and all(
        str(lines.get(line_id, {}).get("type", "subway")) == "tram"
        for line_id in active_stopping_lines
    )

    radius = float(
        styles["STATION_RADIUS_TRANSFER"]
        if is_transfer
        else styles["STATION_RADIUS_NORMAL"]
    )
    stroke_width = float(
        styles["STATION_STROKE_TRANSFER"] if is_transfer else styles["STATION_STROKE"]
    )

    return StationVisualState(
        is_transfer=is_transfer,
        stroke_color=stroke_color,
        text_color_main=text_color_main,
        text_color_sub=text_color_sub,
        radius=radius,
        stroke_width=stroke_width,
        is_tram_station=is_tram_station,
    )


def resolve_station_fonts(
    font_paths: list[str],
    styles: dict[str, float | str],
    *,
    is_tram_station: bool,
) -> StationFonts:
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

    if is_tram_station:
        font_cn = get_font(
            font_paths,
            int(float(styles["FONT_SIZE_LABEL"]) * 0.8),
            priority_index=1,
            weight="Bold",
        )
        font_en = get_font(
            font_paths,
            int(float(styles["FONT_SIZE_LABEL_EN"]) * 0.8),
            priority_index=0,
        )

    return StationFonts(cn=font_cn, en=font_en)


def measure_label_text(
    draw,
    station_id: str,
    station: dict[str, Any],
    fonts: StationFonts,
    scale_factor: int,
    badge_width: float,
    badge_height: float,
) -> LabelTextVariant:
    name_cn = str(station.get("name", {}).get("zh-CN", station_id))
    name_en = str(station.get("name", {}).get("en-US", "")).upper()

    bbox_cn_raw = draw.textbbox((0, 0), name_cn, font=fonts.cn)
    bbox_cn = (
        float(bbox_cn_raw[0]),
        float(bbox_cn_raw[1]),
        float(bbox_cn_raw[2]),
        float(bbox_cn_raw[3]),
    )
    width_cn = float(bbox_cn_raw[2] - bbox_cn_raw[0])
    height_cn = float(bbox_cn_raw[3] - bbox_cn_raw[1])

    width_en = 0.0
    height_en = 0.0
    gap = 0.0
    badge_gap = float(2 * scale_factor)
    if name_en:
        bbox_en_raw = draw.textbbox((0, 0), name_en, font=fonts.en)
        width_en = float(bbox_en_raw[2] - bbox_en_raw[0])
        height_en = float(bbox_en_raw[3] - bbox_en_raw[1])
        gap = float(4 * scale_factor)

    english_y_offset: float | None = None
    badges_y_offset: float | None = None
    block_width = width_cn
    current_height = height_cn

    if name_en:
        english_y_offset = current_height + gap
        current_height = english_y_offset + height_en
        block_width = max(block_width, width_en)

    if badge_width > 0 and badge_height > 0:
        badges_y_offset = current_height + (
            badge_gap if current_height > height_cn else gap
        )
        current_height = badges_y_offset + badge_height
        block_width = max(block_width, badge_width)

    block_height = float(current_height)

    primary = LabelTextMetrics(
        name_cn=name_cn,
        name_en=name_en,
        bbox_cn=bbox_cn,
        width_cn=width_cn,
        height_cn=height_cn,
        width_en=width_en,
        height_en=height_en,
        gap=gap,
        badge_gap=badge_gap,
        badge_width=badge_width,
        badge_height=badge_height,
        english_y_offset=english_y_offset,
        badges_y_offset=badges_y_offset,
        block_width=block_width,
        block_height=block_height,
    )

    compact_badges_y_offset: float | None = None
    compact_height = height_cn
    compact_width = width_cn
    if badge_width > 0 and badge_height > 0:
        compact_badges_y_offset = compact_height + gap
        compact_height = compact_badges_y_offset + badge_height
        compact_width = max(compact_width, badge_width)

    compact = LabelTextMetrics(
        name_cn=name_cn,
        name_en="",
        bbox_cn=bbox_cn,
        width_cn=width_cn,
        height_cn=height_cn,
        width_en=0.0,
        height_en=0.0,
        gap=0.0,
        badge_gap=badge_gap,
        badge_width=badge_width,
        badge_height=badge_height,
        english_y_offset=None,
        badges_y_offset=compact_badges_y_offset,
        block_width=float(compact_width),
        block_height=float(compact_height),
    )

    return LabelTextVariant(primary=primary, compact=compact)
