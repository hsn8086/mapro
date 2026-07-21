from __future__ import annotations

from dataclasses import dataclass
import math

from ..fonts import get_font


@dataclass(frozen=True)
class LegendBlockLayout:
    start_x: float
    start_y: float
    width: float
    height: float


@dataclass(frozen=True)
class LegendRenderData:
    sorted_lines: list[tuple[tuple[int, int | str], str, dict]]
    font: object
    header_font: object
    header_text: str
    start_x: float
    start_y: float
    box_width: float
    box_height: float
    header_height: float
    header_gap: float
    padding_x: float
    padding_y: float
    item_width: float
    item_height: float
    swatch_width: float
    swatch_height: float
    row_gap: float
    col_gap: float
    columns: int
    rows: int


def _build_legend_render_data(
    draw,
    lines: dict,
    font_paths: list[str],
    scale_factor: int,
    canvas_width: int,
    canvas_height: int,
    start_y_override: float | None,
) -> LegendRenderData:
    item_height = 14 * scale_factor
    swatch_width = 18 * scale_factor
    swatch_height = 6 * scale_factor
    font_size = 10 * scale_factor
    padding_x = 12 * scale_factor
    padding_y = 10 * scale_factor
    row_gap = 4 * scale_factor
    col_gap = 14 * scale_factor
    header_gap = 6 * scale_factor

    font = get_font(font_paths, int(font_size))
    header_font = get_font(font_paths, int(font_size * 0.95), 1, weight="Bold")

    sorted_lines = []
    for lid, ldata in lines.items():
        try:
            sort_key = (0, int(lid))
        except ValueError:
            sort_key = (1, lid)
        sorted_lines.append((sort_key, lid, ldata))
    sorted_lines.sort(key=lambda x: x[0])

    max_text_width = 0.0
    for _, _, ldata in sorted_lines:
        name = ldata.get("name", {}).get("zh-CN", "Line")
        bbox = draw.textbbox((0, 0), name, font=font)
        max_text_width = max(max_text_width, float(bbox[2] - bbox[0]))

    # flat spec: no box, no header — swatches sit directly on the canvas
    header_text = ""
    header_height = 0.0
    header_gap = 0.0
    item_width = swatch_width + 12 * scale_factor + max_text_width

    columns = 1
    if (
        len(sorted_lines) >= 4
        and (item_width * 2 + col_gap + padding_x * 2) <= canvas_width * 0.68
    ):
        columns = 2

    rows = max(1, math.ceil(len(sorted_lines) / columns))
    box_width = padding_x * 2 + columns * item_width + (columns - 1) * col_gap
    box_height = (
        padding_y * 2
        + header_height
        + header_gap
        + rows * item_height
        + (rows - 1) * row_gap
    )
    start_x = 20 * scale_factor
    start_y = (
        start_y_override
        if start_y_override is not None
        else canvas_height - box_height - 20 * scale_factor
    )

    return LegendRenderData(
        sorted_lines=sorted_lines,
        font=font,
        header_font=header_font,
        header_text=header_text,
        start_x=float(start_x),
        start_y=float(start_y),
        box_width=float(box_width),
        box_height=float(box_height),
        header_height=header_height,
        header_gap=float(header_gap),
        padding_x=float(padding_x),
        padding_y=float(padding_y),
        item_width=float(item_width),
        item_height=float(item_height),
        swatch_width=float(swatch_width),
        swatch_height=float(swatch_height),
        row_gap=float(row_gap),
        col_gap=float(col_gap),
        columns=columns,
        rows=rows,
    )


def measure_legend_block(
    draw,
    lines: dict,
    font_paths: list[str],
    scale_factor: int,
    canvas_width: int,
    canvas_height: int,
    start_y_override: float | None = None,
) -> LegendBlockLayout:
    data = _build_legend_render_data(
        draw,
        lines,
        font_paths,
        scale_factor,
        canvas_width,
        canvas_height,
        start_y_override,
    )

    return LegendBlockLayout(
        start_x=data.start_x,
        start_y=data.start_y,
        width=data.box_width,
        height=data.box_height,
    )


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
    data = _build_legend_render_data(
        draw,
        lines,
        font_paths,
        scale_factor,
        canvas_width,
        canvas_height,
        start_y_override,
    )
    box_w = data.box_width
    box_h = data.box_height
    start_y = data.start_y
    start_x = data.start_x

    _ = (box_w, box_h, border_color)  # flat spec: no legend box, no header
    items_start_y = start_y + data.padding_y
    for index, (_, _, ldata) in enumerate(data.sorted_lines):
        color = ldata.get("color", "#000000")
        name = ldata.get("name", {}).get("zh-CN", "Line")
        col = index // data.rows
        row = index % data.rows
        cx = start_x + data.padding_x + col * (data.item_width + data.col_gap)
        cy = items_start_y + row * (data.item_height + data.row_gap)
        swatch_y = cy + (data.item_height - data.swatch_height) / 2

        draw.rectangle(
            [cx, swatch_y, cx + data.swatch_width, swatch_y + data.swatch_height],
            fill=color,
            outline=None,
        )

        text_x = cx + data.swatch_width + 8 * scale_factor
        text_y = cy - scale_factor * 0.8
        draw.text((text_x, text_y), name, fill=text_color, font=data.font)
