from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

Point = tuple[int, int]
LabelBox = tuple[float, float, float, float]
LineSegment = tuple[Point, Point]


@dataclass(frozen=True)
class LabelPlacement:
    x: float
    y: float
    box: LabelBox


def is_line_intersecting_rect(
    p1: Point,
    p2: Point,
    rect: LabelBox,
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
            x = x1 + (x2 - x1) * (min_y - y1) / (y2 - y1) if y2 != y1 else x1
            y = min_y
        elif code_out & bottom:
            x = x1 + (x2 - x1) * (max_y - y1) / (y2 - y1) if y2 != y1 else x1
            y = max_y
        elif code_out & right:
            y = y1 + (y2 - y1) * (max_x - x1) / (x2 - x1) if x2 != x1 else y1
            x = max_x
        elif code_out & left:
            y = y1 + (y2 - y1) * (min_x - x1) / (x2 - x1) if x2 != x1 else y1
            x = min_x

        if code_out == code1:
            x1, y1 = x, y
            code1 = compute_out_code(x1, y1)
        else:
            x2, y2 = x, y
            code2 = compute_out_code(x2, y2)


def is_box_colliding_with_lines(
    text_box: LabelBox,
    segments: Sequence[LineSegment],
    threshold: float = 5,
) -> bool:
    for s1, s2 in segments:
        if is_line_intersecting_rect(s1, s2, text_box, padding=threshold):
            return True
    return False


def is_box_overlapping_other_labels(
    text_box: LabelBox,
    existing_boxes: Sequence[LabelBox],
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


def place_label_block(
    pos: Point,
    block_w: float,
    block_h: float,
    line_segments_for_collision: Sequence[LineSegment],
    existing_boxes: Sequence[LabelBox],
    label_offset_base: float,
    scale_factor: int,
) -> LabelPlacement:
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

    for layer_scale in search_layers:
        current_base = label_offset_base * layer_scale

        for dx, dy in base_directions:
            target_cx = pos[0] + dx * (current_base + block_w / 2)
            target_cy = pos[1] + dy * (current_base + block_h / 2)

            tx = target_cx - block_w / 2
            ty = target_cy - block_h / 2
            text_box = (tx, ty, tx + block_w, ty + block_h)

            if is_box_colliding_with_lines(
                text_box,
                line_segments_for_collision,
                threshold=float(5 * scale_factor),
            ):
                continue

            if is_box_overlapping_other_labels(
                text_box,
                existing_boxes,
                padding=float(scale_factor),
            ):
                continue

            return LabelPlacement(x=tx, y=ty, box=text_box)

    fallback_dist = label_offset_base * 1.5
    fallback_x = pos[0] + fallback_dist
    fallback_y = pos[1] - fallback_dist
    return LabelPlacement(
        x=fallback_x,
        y=fallback_y,
        box=(fallback_x, fallback_y, fallback_x + block_w, fallback_y + block_h),
    )
