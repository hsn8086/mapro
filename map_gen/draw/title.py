from __future__ import annotations

import time

from ..fonts import get_font


def draw_title_block(
    draw,
    meta: dict,
    font_paths: list[str],
    styles: dict[str, float | str],
) -> float:
    title_cn = meta.get("name", {}).get("zh-CN", "Metro Map")
    title_en = meta.get("name", {}).get("en-US", "").upper()
    author = meta.get("author", "")

    scale_factor = float(styles["FONT_SIZE_SUBTITLE"]) / 14
    current_y = 30 * scale_factor
    start_x = 30 * scale_factor

    font_size_title = int(styles["FONT_SIZE_TITLE"])
    font_size_subtitle = int(styles["FONT_SIZE_SUBTITLE"])

    draw.text(
        (start_x, current_y),
        title_cn,
        fill=styles["COLOR_TEXT_MAIN"],
        font=get_font(font_paths, font_size_title, 1),
    )
    current_y += font_size_title * 1.6

    if title_en:
        draw.text(
            (start_x, current_y),
            title_en,
            fill=styles["COLOR_TEXT_MAIN"],
            font=get_font(font_paths, int(font_size_title * 0.6), 0, weight="Bold"),
        )
        current_y += font_size_title * 1.0

    if author:
        draw.text(
            (start_x, current_y),
            f"Designed by {author}",
            fill=styles["COLOR_TEXT_SUB"],
            font=get_font(font_paths, font_size_subtitle, 0),
        )
        current_y += font_size_subtitle * 1.5

    draw.text(
        (start_x, current_y),
        f"Updated: {time.strftime('%Y-%m-%d %H:%M')}",
        fill=styles["COLOR_TEXT_SUB"],
        font=get_font(font_paths, font_size_subtitle, 0),
    )

    return current_y
