from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PIL import ImageFont

from .fonts import get_font


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
    block_width: float
    block_height: float


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
        inactive_color = str(styles["COLOR_INACTIVE"])
        stroke_color = inactive_color
        text_color_main = inactive_color
        text_color_sub = inactive_color

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
) -> LabelTextMetrics:
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
    if name_en:
        bbox_en_raw = draw.textbbox((0, 0), name_en, font=fonts.en)
        width_en = float(bbox_en_raw[2] - bbox_en_raw[0])
        height_en = float(bbox_en_raw[3] - bbox_en_raw[1])
        gap = float(5 * scale_factor)

    row1_width = float(width_cn + badge_width)
    block_width = float(max(row1_width, width_en))
    block_height = float(max(height_cn, badge_height) + gap + height_en)

    return LabelTextMetrics(
        name_cn=name_cn,
        name_en=name_en,
        bbox_cn=bbox_cn,
        width_cn=width_cn,
        height_cn=height_cn,
        width_en=width_en,
        height_en=height_en,
        gap=gap,
        block_width=block_width,
        block_height=block_height,
    )
