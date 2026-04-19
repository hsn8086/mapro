from __future__ import annotations

import time
from dataclasses import dataclass

from ..fonts import get_font


@dataclass(frozen=True)
class TitleLineLayout:
    text: str
    x: float
    y: float
    fill: str
    font: object
    bbox: tuple[float, float, float, float]


@dataclass(frozen=True)
class TitleBlockLayout:
    start_x: float
    start_y: float
    width: float
    height: float
    lines: tuple[TitleLineLayout, ...]


def _build_meta_text(meta: dict) -> str:
    author = meta.get("author", "")
    parts: list[str] = []
    if author:
        parts.append(f"Designed by {author}")
    parts.append(f"Updated: {time.strftime('%Y-%m-%d %H:%M')}")
    return "  ·  ".join(parts)


def _measure_text_bbox(
    draw, text: str, font: object
) -> tuple[float, float, float, float]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))


def measure_title_block(
    draw,
    meta: dict,
    font_paths: list[str],
    styles: dict[str, float | str],
) -> TitleBlockLayout:
    title_cn = meta.get("name", {}).get("zh-CN", "Metro Map")
    title_en = meta.get("name", {}).get("en-US", "").upper()
    meta_text = _build_meta_text(meta)

    scale_factor = float(styles["FONT_SIZE_SUBTITLE"]) / 14
    start_x = 24 * scale_factor
    start_y = 16 * scale_factor
    max_width = 0.0
    lines: list[TitleLineLayout] = []

    title_cn_font = get_font(font_paths, int(styles["FONT_SIZE_TITLE"]), 1)
    title_en_font = get_font(
        font_paths, int(int(styles["FONT_SIZE_TITLE"]) * 0.6), 0, weight="Bold"
    )
    meta_font = get_font(font_paths, int(styles["FONT_SIZE_SUBTITLE"]), 0)

    def append_line(text: str, font: object, fill: str, gap: float) -> None:
        nonlocal max_width
        bbox = _measure_text_bbox(draw, text, font)
        if not lines:
            y = start_y - bbox[1]
        else:
            previous = lines[-1]
            y = previous.y + previous.bbox[3] + gap - bbox[1]

        lines.append(
            TitleLineLayout(
                text=text,
                x=start_x,
                y=y,
                fill=fill,
                font=font,
                bbox=bbox,
            )
        )
        max_width = max(max_width, bbox[2] - bbox[0])

    append_line(title_cn, title_cn_font, str(styles["COLOR_TEXT_MAIN"]), 0.0)
    if title_en:
        append_line(
            title_en, title_en_font, str(styles["COLOR_TEXT_SUB"]), 3 * scale_factor
        )
    append_line(meta_text, meta_font, str(styles["COLOR_TEXT_SUB"]), 6 * scale_factor)

    last_line = lines[-1]
    occupied_bottom = last_line.y + last_line.bbox[3]

    return TitleBlockLayout(
        start_x=start_x,
        start_y=start_y,
        width=max_width,
        height=occupied_bottom - start_y,
        lines=tuple(lines),
    )


def draw_title_block(
    draw,
    meta: dict,
    font_paths: list[str],
    styles: dict[str, float | str],
) -> float:
    layout = measure_title_block(draw, meta, font_paths, styles)
    for line in layout.lines:
        draw.text((line.x, line.y), line.text, fill=line.fill, font=line.font)
    return layout.start_y + layout.height
