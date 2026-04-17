from __future__ import annotations

from ..fonts import get_font


def draw_legend(
    draw,
    lines: dict,
    font_paths: list[str],
    scale_factor: int,
    canvas_width: int,
    canvas_height: int,
    text_color: str,
    border_color: str,
    start_y_override: float | None = None,
) -> None:
    item_height = 30 * scale_factor
    icon_size = 14 * scale_factor
    font_size = 14 * scale_factor
    padding = 25 * scale_factor

    font = get_font(font_paths, int(font_size))

    sorted_lines = []
    for lid, ldata in lines.items():
        try:
            sort_key = (0, int(lid))
        except ValueError:
            sort_key = (1, lid)
        sorted_lines.append((sort_key, lid, ldata))

    sorted_lines.sort(key=lambda x: x[0])

    max_text_w = 0
    for _, _, ldata in sorted_lines:
        name = ldata.get("name", {}).get("zh-CN", "Line")
        bbox = draw.textbbox((0, 0), name, font=font)
        max_text_w = max(max_text_w, bbox[2] - bbox[0])

    box_w = icon_size + 20 * scale_factor + max_text_w + padding * 2
    box_h = len(sorted_lines) * item_height + padding * 2 - (item_height - icon_size)

    if start_y_override:
        start_y = start_y_override
    else:
        start_y = 110 * scale_factor

    start_x = 30 * scale_factor

    draw.rectangle(
        [start_x, start_y, start_x + box_w, start_y + box_h],
        fill="white",
        outline=border_color,
        width=1,
    )

    cx = start_x + padding
    cy = start_y + padding

    for _, _, ldata in sorted_lines:
        color = ldata.get("color", "#000000")
        name = ldata.get("name", {}).get("zh-CN", "Line")

        draw.rectangle(
            [cx, cy, cx + icon_size, cy + icon_size], fill=color, outline=None
        )

        text_x = cx + icon_size + 15 * scale_factor
        text_y = cy - (scale_factor * 2)
        draw.text((text_x, text_y), name, fill=text_color, font=font)

        cy += item_height
