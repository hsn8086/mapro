from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .label_context import DEFAULT_DIRECTIONS, LocalLabelContext

Point = tuple[int, int]
LabelBox = tuple[float, float, float, float]
LineSegment = tuple[Point, Point]


@dataclass(frozen=True)
class LabelPlacement:
    x: float
    y: float
    box: LabelBox
    score: float


@dataclass(frozen=True)
class LabelCandidate:
    placement: LabelPlacement
    score: float


def compute_leader_line(
    pos: Point,
    text_box: LabelBox,
    station_radius: float,
    scale_factor: int,
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    anchor_x = min(max(float(pos[0]), text_box[0]), text_box[2])
    anchor_y = min(max(float(pos[1]), text_box[1]), text_box[3])
    dx = anchor_x - pos[0]
    dy = anchor_y - pos[1]
    distance = (dx * dx + dy * dy) ** 0.5
    if distance <= station_radius + 6 * scale_factor:
        return None

    ux = dx / distance
    uy = dy / distance
    start = (
        pos[0] + ux * (station_radius + 1.5 * scale_factor),
        pos[1] + uy * (station_radius + 1.5 * scale_factor),
    )
    end = (
        anchor_x - ux * (2.0 * scale_factor),
        anchor_y - uy * (2.0 * scale_factor),
    )
    return (start, end)


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
    local_context: LocalLabelContext | None = None,
) -> LabelPlacement:
    search_layers = [1.0, 1.3, 1.6]
    if local_context and local_context.dense:
        search_layers.extend([2.0, 2.4, 2.8, 3.2, 3.8, 4.4])
    base_directions = (
        local_context.preferred_directions if local_context else DEFAULT_DIRECTIONS
    )

    best_candidate: LabelCandidate | None = None
    best_line_clear_candidate: LabelCandidate | None = None
    best_overlap_clear_candidate: LabelCandidate | None = None
    best_relaxed_candidate: LabelCandidate | None = None

    def nearest_box_distance(text_box: LabelBox) -> float:
        if not existing_boxes:
            return 999999.0

        t0x, t0y, t1x, t1y = text_box
        min_distance = 999999.0
        for e0x, e0y, e1x, e1y in existing_boxes:
            dx = max(e0x - t1x, t0x - e1x, 0.0)
            dy = max(e0y - t1y, t0y - e1y, 0.0)
            min_distance = min(min_distance, (dx * dx + dy * dy) ** 0.5)
        return min_distance

    def nearest_neighbor_distance(text_box: LabelBox) -> float:
        if not local_context or not local_context.nearby_stations:
            return 999999.0

        cx = (text_box[0] + text_box[2]) / 2
        cy = (text_box[1] + text_box[3]) / 2
        min_distance = 999999.0
        for station in local_context.nearby_stations:
            dx = cx - station.pos[0]
            dy = cy - station.pos[1]
            min_distance = min(min_distance, (dx * dx + dy * dy) ** 0.5)
        return min_distance

    for layer_scale in search_layers:
        current_base = label_offset_base * layer_scale

        for dx, dy in base_directions:
            target_cx = pos[0] + dx * (current_base + block_w / 2)
            target_cy = pos[1] + dy * (current_base + block_h / 2)

            tx = target_cx - block_w / 2
            ty = target_cy - block_h / 2
            text_box = (tx, ty, tx + block_w, ty + block_h)

            line_collision = is_box_colliding_with_lines(
                text_box,
                line_segments_for_collision,
                threshold=float(5 * scale_factor),
            )
            label_overlap = is_box_overlapping_other_labels(
                text_box,
                existing_boxes,
                padding=float(scale_factor),
            )

            if local_context and local_context.dense:
                preferred_rank = local_context.preferred_directions.index((dx, dy))
                direction_score = preferred_rank * 0.22
                if dx == 0:
                    direction_score += 0.05
                if dy > 0:
                    direction_score += 0.08
            else:
                direction_score = 0.0
                if dx == 1 and dy == 0:
                    direction_score = 0.0
                elif dx == 1:
                    direction_score = 0.25
                elif dx == 0:
                    direction_score = 0.6
                else:
                    direction_score = 1.0

            vertical_penalty = 0.0 if dy <= 0 else 0.2
            layer_penalty = (layer_scale - 1.0) * 2.0
            distance_penalty = abs(tx - pos[0]) / max(block_w, 1.0) * 0.05
            label_clearance_penalty = 0.0
            nearest_label_gap = nearest_box_distance(text_box)
            if nearest_label_gap < 12 * scale_factor:
                label_clearance_penalty = (12 * scale_factor - nearest_label_gap) * 0.04

            neighbor_anchor_penalty = 0.0
            nearest_neighbor_gap = nearest_neighbor_distance(text_box)
            if nearest_neighbor_gap < 24 * scale_factor:
                neighbor_anchor_penalty = (
                    24 * scale_factor - nearest_neighbor_gap
                ) * 0.05

            base_score = (
                direction_score
                + vertical_penalty
                + layer_penalty
                + distance_penalty
                + label_clearance_penalty
                + neighbor_anchor_penalty
            )
            score = base_score
            if label_overlap:
                score += 40.0
            if line_collision:
                score += 80.0
            candidate = LabelCandidate(
                placement=LabelPlacement(x=tx, y=ty, box=text_box, score=score),
                score=score,
            )

            if (
                best_relaxed_candidate is None
                or candidate.score < best_relaxed_candidate.score
            ):
                best_relaxed_candidate = candidate

            if not line_collision and (
                best_line_clear_candidate is None
                or candidate.score < best_line_clear_candidate.score
            ):
                best_line_clear_candidate = candidate

            if not label_overlap and (
                best_overlap_clear_candidate is None
                or candidate.score < best_overlap_clear_candidate.score
            ):
                best_overlap_clear_candidate = candidate

            if line_collision or label_overlap:
                continue

            if best_candidate is None or candidate.score < best_candidate.score:
                best_candidate = candidate

    if best_candidate is not None:
        return best_candidate.placement

    if best_line_clear_candidate is not None:
        return best_line_clear_candidate.placement

    if best_overlap_clear_candidate is not None:
        return best_overlap_clear_candidate.placement

    if best_relaxed_candidate is not None:
        return best_relaxed_candidate.placement

    fallback_dist = label_offset_base * 1.5
    fallback_x = pos[0] + fallback_dist
    fallback_y = pos[1] - fallback_dist
    return LabelPlacement(
        x=fallback_x,
        y=fallback_y,
        box=(fallback_x, fallback_y, fallback_x + block_w, fallback_y + block_h),
        score=999999.0,
    )
