from __future__ import annotations

from typing import Callable

from ..fonts import get_font


def draw_dashed_line(
    draw_obj,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    fill: str = "black",
    width: int = 1,
    dash_len: float = 10,
    gap_len: float = 8,
) -> None:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dist = (dx * dx + dy * dy) ** 0.5
    if dist == 0:
        return

    ux = dx / dist
    uy = dy / dist

    curr_dist = 0
    while curr_dist < dist:
        segment_end_dist = min(curr_dist + dash_len, dist)
        p_a = (start[0] + ux * curr_dist, start[1] + uy * curr_dist)
        p_b = (start[0] + ux * segment_end_dist, start[1] + uy * segment_end_dist)
        draw_obj.line([p_a, p_b], fill=fill, width=width)
        curr_dist += dash_len + gap_len


def draw_orthogonal_dashed_connection(
    draw_obj,
    p1: tuple[float, float],
    p2: tuple[float, float],
    scale_factor: int,
    *,
    fill: str = "black",
    width: int = 1,
    dash_len: float = 10,
    gap_len: float = 8,
) -> tuple[float, float] | None:
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    align_threshold = float(10 * scale_factor)
    offset_dist = float(25 * scale_factor)

    points: list[tuple[float, float]] = []
    label_pos = None

    if abs(dx) < align_threshold:
        p_a = (p1[0] + offset_dist, p1[1])
        p_b = (p2[0] + offset_dist, p2[1])

        points = [p1, p_a, p_b, p2]
        label_pos = (
            (p_a[0] + p_b[0]) / 2 + float(5 * scale_factor),
            (p_a[1] + p_b[1]) / 2,
        )
    elif abs(dy) < align_threshold:
        p_a = (p1[0], p1[1] - offset_dist)
        p_b = (p2[0], p2[1] - offset_dist)

        points = [p1, p_a, p_b, p2]
        label_pos = (
            (p_a[0] + p_b[0]) / 2,
            (p_a[1] + p_b[1]) / 2 - float(10 * scale_factor),
        )
    else:
        corner = (p2[0], p1[1])
        points = [p1, corner, p2]
        label_pos = (corner[0], corner[1] - float(10 * scale_factor))

    for i in range(len(points) - 1):
        draw_dashed_line(
            draw_obj,
            points[i],
            points[i + 1],
            fill=fill,
            width=width,
            dash_len=dash_len,
            gap_len=gap_len,
        )

    return label_pos


def draw_transfer_connections(
    draw,
    connections: list[dict],
    get_pos: Callable[[str], tuple[int, int] | None],
    scale_factor: int,
    font_paths: list[str],
    styles: dict[str, float | str],
) -> None:
    font_conn = get_font(
        font_paths,
        int(float(styles["FONT_SIZE_LABEL_EN"]) * 0.9),
        priority_index=1,
        weight="Regular",
    )

    for conn in connections:
        sid1 = conn.get("fromStationId")
        sid2 = conn.get("toStationId")
        c_type = conn.get("type", "physical")

        if not sid1 or not sid2:
            continue

        p1 = get_pos(sid1)
        p2 = get_pos(sid2)

        if not p1 or not p2:
            continue

        conn_color = str(styles.get("COLOR_CONNECTION_PHYSICAL", "#7f8c8d"))
        conn_width = int(2 * scale_factor)

        label_text = ""
        is_dashed = False

        if c_type == "virtual":
            label_text = "出站换乘"
            is_dashed = True
            conn_color = str(styles.get("COLOR_CONNECTION_VIRTUAL", "#95a5a6"))
        elif c_type == "bus":
            label_text = "接驳公交"
            is_dashed = True
            conn_color = str(styles.get("COLOR_CONNECTION_BUS", "#e67e22"))
        elif c_type == "physical":
            label_text = "同站换乘"
            is_dashed = False

        label_anchor = None
        if is_dashed:
            label_anchor = draw_orthogonal_dashed_connection(
                draw,
                (float(p1[0]), float(p1[1])),
                (float(p2[0]), float(p2[1])),
                scale_factor,
                fill=conn_color,
                width=conn_width,
                dash_len=float(6 * scale_factor),
                gap_len=float(4 * scale_factor),
            )
        else:
            draw.line([p1, p2], fill=conn_color, width=conn_width)
            label_anchor = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)

        if label_text and label_anchor:
            tx, ty = label_anchor

            if not is_dashed:
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                dist = (dx * dx + dy * dy) ** 0.5
                offset_dist = float(8 * scale_factor)

                if dist > 0:
                    ux = -dy / dist
                    uy = dx / dist
                    tx = tx + ux * offset_dist
                    ty = ty + uy * offset_dist

            bbox = draw.textbbox((0, 0), label_text, font=font_conn)
            tw = float(bbox[2] - bbox[0])
            th = float(bbox[3] - bbox[1])

            draw.text(
                (tx - tw / 2, ty - th / 2),
                label_text,
                fill=conn_color,
                font=font_conn,
            )
