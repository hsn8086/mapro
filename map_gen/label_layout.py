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
    segment_extents: dict[LineSegment, float] | None = None,
) -> bool:
    for s1, s2 in segments:
        padding = threshold
        if segment_extents is not None:
            padding += segment_extents.get((s1, s2), 0.0)
        if is_line_intersecting_rect(s1, s2, text_box, padding=padding):
            return True
    return False


_AXIS_DIRECTION_RANKS: dict[tuple[int, int], tuple[tuple[int, int], ...]] = {
    # horizontal run: label below, then above, then trailing quadrants
    (1, 0): ((0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1), (1, 0), (-1, 0)),
    # vertical run: label beside, right first
    (0, 1): ((1, 0), (-1, 0), (1, -1), (1, 1), (-1, -1), (-1, 1), (0, -1), (0, 1)),
    # down-right diagonal: clear quadrants are upper-right / lower-left
    (1, 1): ((1, -1), (-1, 1), (1, 0), (0, 1), (0, -1), (-1, 0), (1, 1), (-1, -1)),
    # up-right diagonal: clear quadrants are lower-right / upper-left
    (1, -1): ((1, 1), (-1, -1), (1, 0), (0, 1), (0, -1), (-1, 0), (1, -1), (-1, 1)),
}


def axis_direction_ranks(
    axis_dir: tuple[int, int] | None,
) -> tuple[tuple[int, int], ...] | None:
    if axis_dir is None:
        return None
    dx, dy = axis_dir
    if dx < 0 or (dx == 0 and dy < 0):
        dx, dy = -dx, -dy
    return _AXIS_DIRECTION_RANKS.get((dx, dy))


_SLIDE_FRACTIONS_CARDINAL: tuple[float, ...] = (0.125, 0.25, 0.375, 0.5)
_SLIDE_FRACTIONS_DIAGONAL: tuple[float, ...] = (0.25, 0.5)


def slide_offsets(
    direction: tuple[int, int],
    block_w: float,
    block_h: float,
) -> tuple[tuple[float, float], ...]:
    """Lateral shifts that let a label tuck into a gap beside its ray.

    Sliding happens along the axis perpendicular to the placement
    direction; diagonal directions may slide on either axis. Cardinal
    directions use a finer step so labels can slip into tight pockets.
    """
    dx, dy = direction
    offsets: list[tuple[float, float]] = []
    if dx != 0 and dy != 0:
        for fraction in _SLIDE_FRACTIONS_DIAGONAL:
            offsets.append((-fraction * block_w, 0.0))
            offsets.append((fraction * block_w, 0.0))
            offsets.append((0.0, -fraction * block_h))
            offsets.append((0.0, fraction * block_h))
        return tuple(offsets)
    for fraction in _SLIDE_FRACTIONS_CARDINAL:
        if dx == 0:
            offsets.append((-fraction * block_w, 0.0))
            offsets.append((fraction * block_w, 0.0))
        else:
            offsets.append((0.0, -fraction * block_h))
            offsets.append((0.0, fraction * block_h))
    return tuple(offsets)


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
    *,
    axis_dir: tuple[int, int] | None = None,
    obstacle_boxes: Sequence[LabelBox] = (),
    segment_extents: dict[LineSegment, float] | None = None,
    soft_line_segments: Sequence[LineSegment] = (),
) -> LabelPlacement:
    search_layers = [1.0, 1.3, 1.6]
    if local_context and local_context.dense:
        search_layers.extend([2.0, 2.4, 2.8, 3.2, 3.8, 4.4])
    axis_ranks = axis_direction_ranks(axis_dir)
    if local_context and local_context.dense:
        base_directions = local_context.preferred_directions
    elif axis_ranks is not None:
        base_directions = axis_ranks
    else:
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

    def reading_distance(text_box: LabelBox, point: Point) -> float:
        """Perceived anchor distance from a label box to a station.

        A station vertically aligned with the text band reads as the
        label's anchor much more strongly, so aligned stations count as
        closer than their raw rectangle distance.
        """
        dx = max(text_box[0] - point[0], point[0] - text_box[2], 0.0)
        dy = max(text_box[1] - point[1], point[1] - text_box[3], 0.0)
        distance = (dx * dx + dy * dy) ** 0.5
        if text_box[1] <= point[1] <= text_box[3]:
            distance *= 0.6
        return distance

    def anchor_ambiguity_penalty(text_box: LabelBox) -> float:
        """Penalty when the box reads as belonging to a neighbouring station.

        The margin by which a neighbour is perceptually closer than the
        label's own station is charged against the candidate.
        """
        if not local_context or not local_context.nearby_stations:
            return 0.0

        own_distance = reading_distance(text_box, pos)
        worst_margin = 0.0
        for station in local_context.nearby_stations:
            neighbor_distance = reading_distance(text_box, station.pos)
            if neighbor_distance < own_distance:
                worst_margin = max(worst_margin, own_distance - neighbor_distance)
        return min(worst_margin, 40.0 * scale_factor) * 0.06

    def direction_score_for(dx: int, dy: int) -> float:
        if local_context and local_context.dense:
            preferred_rank = local_context.preferred_directions.index((dx, dy))
            direction_score = preferred_rank * 0.22
            if dx == 0:
                direction_score += 0.05
            if dy > 0:
                direction_score += 0.08
            return direction_score
        if axis_ranks is not None:
            return axis_ranks.index((dx, dy)) * 0.25
        if dx == 1 and dy == 0:
            return 0.0
        if dx == 1:
            return 0.25
        if dx == 0:
            return 0.6
        return 1.0

    def evaluate_candidate(
        tx: float,
        ty: float,
        dx: int,
        dy: int,
        layer_scale: float,
        extra_penalty: float,
    ) -> tuple[bool, bool]:
        nonlocal best_candidate
        nonlocal best_line_clear_candidate
        nonlocal best_overlap_clear_candidate
        nonlocal best_relaxed_candidate

        text_box = (tx, ty, tx + block_w, ty + block_h)
        line_collision = is_box_colliding_with_lines(
            text_box,
            line_segments_for_collision,
            threshold=float(3 * scale_factor),
            segment_extents=segment_extents,
        )
        if not line_collision and obstacle_boxes:
            line_collision = is_box_overlapping_other_labels(
                text_box,
                obstacle_boxes,
                padding=float(scale_factor),
            )
        # planned / under-construction strokes are soft obstacles:
        # avoid them when possible, but prefer covering them over
        # covering an in-service line or another label
        soft_collision = bool(soft_line_segments) and is_box_colliding_with_lines(
            text_box,
            soft_line_segments,
            threshold=float(3 * scale_factor),
            segment_extents=segment_extents,
        )
        label_overlap = is_box_overlapping_other_labels(
            text_box,
            existing_boxes,
            padding=float(scale_factor),
        )

        vertical_penalty = 0.0 if (dy <= 0 or axis_ranks is not None) else 0.2
        layer_penalty = (layer_scale - 1.0) * 2.0
        distance_penalty = abs(tx - pos[0]) / max(block_w, 1.0) * 0.05
        label_clearance_penalty = 0.0
        nearest_label_gap = nearest_box_distance(text_box)
        if nearest_label_gap < 12 * scale_factor:
            label_clearance_penalty = (12 * scale_factor - nearest_label_gap) * 0.04

        neighbor_anchor_penalty = 0.0
        nearest_neighbor_gap = nearest_neighbor_distance(text_box)
        if nearest_neighbor_gap < 24 * scale_factor:
            neighbor_anchor_penalty = (24 * scale_factor - nearest_neighbor_gap) * 0.05

        score = (
            direction_score_for(dx, dy)
            + vertical_penalty
            + layer_penalty
            + distance_penalty
            + label_clearance_penalty
            + neighbor_anchor_penalty
            + anchor_ambiguity_penalty(text_box)
            + extra_penalty
        )
        if soft_collision:
            score += 8.0
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

        clean = not (line_collision or label_overlap)
        if clean and (best_candidate is None or candidate.score < best_candidate.score):
            best_candidate = candidate
        return clean, soft_collision

    for layer_scale in search_layers:
        current_base = label_offset_base * layer_scale

        for dx, dy in base_directions:
            target_cx = pos[0] + dx * (current_base + block_w / 2)
            target_cy = pos[1] + dy * (current_base + block_h / 2)

            tx = target_cx - block_w / 2
            ty = target_cy - block_h / 2

            clean, soft = evaluate_candidate(tx, ty, dx, dy, layer_scale, 0.0)
            if clean and not soft:
                continue
            # blocked or covering a soft obstacle: try tucking the label
            # into a nearby gap by sliding perpendicular to the ray
            for shift_x, shift_y in slide_offsets((dx, dy), block_w, block_h):
                # charge slides by displacement, but never more than the
                # equivalent block fraction: a quarter-block tuck must stay
                # affordable even for wide labels
                absolute_cost = (abs(shift_x) + abs(shift_y)) / max(
                    label_offset_base, 1.0
                )
                fractional_cost = (
                    abs(shift_x) / max(block_w, 1.0) + abs(shift_y) / max(block_h, 1.0)
                ) * 2.0
                slide_penalty = min(absolute_cost, fractional_cost) * 0.7
                evaluate_candidate(
                    tx + shift_x,
                    ty + shift_y,
                    dx,
                    dy,
                    layer_scale,
                    slide_penalty,
                )

        # deeper layers cost at least (layer - 1) * 2.0, so stop early once
        # a clean candidate already beats anything they could produce
        layer_index = search_layers.index(layer_scale)
        if layer_index + 1 < len(search_layers) and best_candidate is not None:
            next_layer_floor = (search_layers[layer_index + 1] - 1.0) * 2.0
            if best_candidate.score <= next_layer_floor:
                break

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
