from __future__ import annotations

import math
import os
from dataclasses import dataclass

from PIL import Image

from ..label_context import StationContextInput, build_local_label_contexts
from ..label_layout import LabelPlacement, compute_leader_line, place_label_block
from ..station_badges import (
    BadgeMetrics,
    BadgeVariant,
    collect_facility_tags,
    draw_badges,
    measure_badges,
)
from ..station_labeling import (
    LabelTextVariant,
    LabelTextMetrics,
    StationFonts,
    StationVisualState,
    build_station_visual_state,
    measure_label_text,
    resolve_station_fonts,
)
from ..stroke_builder import StrokeArc, StrokeElement
from ..station_symbols import (
    StationSymbol,
    build_station_symbol,
    fit_junction_spread,
    find_station_axes,
    render_station_symbol,
)

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
_TOILET_INSIDE_PATH = os.path.join(_ASSETS_DIR, "toilet_inside.png")
_TOILET_OUTSIDE_PATH = os.path.join(_ASSETS_DIR, "toilet_outside.png")
TOILET_ICON_INSIDE: Image.Image | None = None
TOILET_ICON_OUTSIDE: Image.Image | None = None


def _line_corner_pose(
    pos: tuple[int, int],
    polyline: list[tuple[int, int]],
    corner_radius: float,
) -> tuple[tuple[float, float], tuple[float, float], tuple[int, int]] | None:
    """Pose of one line's stroke where it turns at pos (see _corner_symbol_pose)."""
    for index in range(1, len(polyline) - 1):
        if polyline[index] != pos:
            continue
        prev_pt = polyline[index - 1]
        next_pt = polyline[index + 1]
        len_in = math.hypot(pos[0] - prev_pt[0], pos[1] - prev_pt[1])
        len_out = math.hypot(next_pt[0] - pos[0], next_pt[1] - pos[1])
        if len_in < 1e-9 or len_out < 1e-9:
            continue
        dir_in = ((pos[0] - prev_pt[0]) / len_in, (pos[1] - prev_pt[1]) / len_in)
        dir_out = (
            (next_pt[0] - pos[0]) / len_out,
            (next_pt[1] - pos[1]) / len_out,
        )
        cross = dir_in[0] * dir_out[1] - dir_in[1] * dir_out[0]
        if abs(cross) < 1e-9:
            continue
        dir_to_prev = (-dir_in[0], -dir_in[1])
        dot = max(
            -1.0,
            min(
                1.0,
                dir_to_prev[0] * dir_out[0] + dir_to_prev[1] * dir_out[1],
            ),
        )
        turn_angle = math.acos(dot)
        if turn_angle <= 1e-6 or abs(turn_angle - math.pi) <= 1e-6:
            continue
        limit = min(len_in, len_out) * 0.45 * math.tan(turn_angle / 2.0)
        radius = min(corner_radius, limit)
        if radius <= 0.5:
            return None
        bis_x = dir_to_prev[0] + dir_out[0]
        bis_y = dir_to_prev[1] + dir_out[1]
        bis_len = math.hypot(bis_x, bis_y)
        if bis_len < 1e-9:
            continue
        bisector = (bis_x / bis_len, bis_y / bis_len)
        center_distance = radius / math.sin(turn_angle / 2.0)
        center = (
            pos[0] + bisector[0] * center_distance,
            pos[1] + bisector[1] * center_distance,
        )
        radial = (pos[0] - center[0], pos[1] - center[1])
        radial_len = math.hypot(radial[0], radial[1])
        if radial_len < 1e-9:
            continue
        radial_normal = (radial[0] / radial_len, radial[1] / radial_len)
        midpoint = (
            center[0] + radial_normal[0] * radius,
            center[1] + radial_normal[1] * radius,
        )
        tangent = (
            dir_in[0] + dir_out[0],
            dir_in[1] + dir_out[1],
        )
        tangent_dir = (
            (0 if abs(tangent[0]) < 1e-9 else (1 if tangent[0] > 0 else -1)),
            (0 if abs(tangent[1]) < 1e-9 else (1 if tangent[1] > 0 else -1)),
        )
        return (midpoint, radial_normal, tangent_dir)
    return None


def _corner_symbol_pose(
    pos: tuple[int, int],
    station_line_ids: list[str],
    line_polylines: dict[str, list[tuple[int, int]]],
    corner_radius: float,
) -> tuple[tuple[float, float], tuple[float, float], tuple[int, int]] | None:
    """Pose for a station sitting exactly on a rounded corner vertex.

    The stroke is pulled inward by the corner fillet, so the symbol must
    move onto the arc midpoint and orient along the radial direction.
    Returns (midpoint, radial_normal, tangent_dir) or None if the station
    is not on a turning vertex.
    """
    candidates = list(station_line_ids) + [
        lid for lid in line_polylines if lid not in station_line_ids
    ]
    for line_id in candidates:
        polyline = line_polylines.get(line_id, [])
        pose = _line_corner_pose(pos, polyline, corner_radius)
        if pose is not None:
            return pose
        # only inspect the first polyline that actually contains the vertex
        if any(point == pos for point in polyline):
            return None
    return None


def _closest_point_on_stroke(
    element: StrokeElement,
    point: tuple[float, float],
) -> tuple[float, float]:
    """Closest point of a drawn stroke element to point."""
    if isinstance(element, StrokeArc):
        # match the winding the renderer uses, or we would test against
        # the complementary arc and land on the wrong side of the circle
        start_angle = element.start_angle
        end_angle = element.end_angle
        if element.clockwise:
            while end_angle >= start_angle:
                end_angle -= 2 * math.pi
        else:
            while end_angle <= start_angle:
                end_angle += 2 * math.pi
        span = end_angle - start_angle

        radial = (point[0] - element.center[0], point[1] - element.center[1])
        if math.hypot(radial[0], radial[1]) > 1e-9:
            delta = math.atan2(radial[1], radial[0]) - start_angle
            two_pi = 2 * math.pi
            if span >= 0:
                delta -= two_pi * math.floor(delta / two_pi)
                inside = delta <= span
            else:
                delta -= two_pi * math.ceil(delta / two_pi)
                inside = delta >= span
            if inside:
                angle = start_angle + delta
                return (
                    element.center[0] + math.cos(angle) * element.radius,
                    element.center[1] + math.sin(angle) * element.radius,
                )
        ends = (element.start, element.end)
        return min(
            ends, key=lambda end: math.hypot(end[0] - point[0], end[1] - point[1])
        )
    start, end = element.start, element.end
    dx, dy = end[0] - start[0], end[1] - start[1]
    length_squared = dx * dx + dy * dy
    if length_squared < 1e-12:
        return start
    t = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length_squared
    t = max(0.0, min(1.0, t))
    return (start[0] + t * dx, start[1] + t * dy)


def _station_track_points(
    pos: tuple[int, int],
    station_line_ids: list[str],
    strokes_by_line: dict[str, list[StrokeElement]],
    search_radius: float,
) -> list[tuple[float, float]]:
    """Where each of the station's own lines actually lays its ink.

    Read off the strokes as built - chamfered corners included - rather
    than re-derived from the polyline, because a line turning at the
    station no longer covers the vertex it turns on.
    """
    anchor = (float(pos[0]), float(pos[1]))
    points: list[tuple[float, float]] = []
    for line_id in station_line_ids:
        best: tuple[float, float] | None = None
        best_distance = search_radius
        for element in strokes_by_line.get(line_id, []):
            if element.is_overlay:
                continue
            candidate = _closest_point_on_stroke(element, anchor)
            distance = math.hypot(candidate[0] - anchor[0], candidate[1] - anchor[1])
            if distance < best_distance:
                best_distance = distance
                best = candidate
        if best is not None:
            points.append(best)
    return points


def _choose_station_axis(
    pos: tuple[int, int],
    station_line_ids: list[str],
    line_polylines: dict[str, list[tuple[int, int]]],
    segment_map: dict,
    bundle_offsets: dict,
) -> tuple[tuple[float, float], tuple, list[float]] | None:
    """Pick the axis whose strokes (of this station's own lines) span widest.

    At corner vertices a station sits on several segments; the bundle
    corridor (largest lateral span) wins so interchange capsules cover
    every stroke and slots land inside the offset stroke, not the axis.
    """
    best: tuple[tuple[float, float], tuple, list[float]] | None = None
    best_score: tuple[float, int] = (-1.0, -1)
    for normal, key in find_station_axes(pos, station_line_ids, line_polylines):
        members = segment_map.get(key, [])
        own = [lid for lid in station_line_ids if lid in members]
        laterals = [float(bundle_offsets.get((lid, key), 0.0)) for lid in own] or [0.0]
        score = (max(laterals) - min(laterals), len(own))
        if score > best_score:
            best_score = score
            best = (normal, key, laterals)
    return best


@dataclass(frozen=True)
class MeasuredStation:
    station_id: str
    station: dict
    pos: tuple[int, int]
    visual_state: StationVisualState
    station_fonts: StationFonts
    badge_variant: BadgeVariant
    text_variant: LabelTextVariant
    symbol: StationSymbol | None = None
    axis_dir: tuple[int, int] | None = None


def draw_stations(
    img,
    draw,
    stations: dict,
    lines: dict,
    get_pos,
    skip_map: set[tuple[str, str]],
    station_markers: dict[str, list[dict]],
    line_segments_for_collision: list[tuple[tuple[int, int], tuple[int, int]]],
    tram_line_segments_for_collision: list[tuple[tuple[int, int], tuple[int, int]]],
    scale_factor: int,
    font_paths: list[str],
    styles: dict[str, float | str],
    *,
    line_polylines: dict[str, list[tuple[int, int]]] | None = None,
    segment_map: dict | None = None,
    bundle_offsets: dict | None = None,
    badges_enabled: bool = True,
    soft_line_segments: list[tuple[tuple[int, int], tuple[int, int]]] | None = None,
    line_strokes: list[StrokeElement] | None = None,
) -> None:
    global TOILET_ICON_INSIDE, TOILET_ICON_OUTSIDE
    line_polylines = line_polylines or {}
    segment_map = segment_map or {}
    bundle_offsets = bundle_offsets or {}
    soft_line_segments = soft_line_segments or []
    strokes_by_line: dict[str, list[StrokeElement]] = {}
    for element in line_strokes or []:
        strokes_by_line.setdefault(element.line_id, []).append(element)
    if TOILET_ICON_INSIDE is None and os.path.exists(_TOILET_INSIDE_PATH):
        TOILET_ICON_INSIDE = Image.open(_TOILET_INSIDE_PATH).convert("RGBA")
    if TOILET_ICON_OUTSIDE is None and os.path.exists(_TOILET_OUTSIDE_PATH):
        TOILET_ICON_OUTSIDE = Image.open(_TOILET_OUTSIDE_PATH).convert("RGBA")

    measured_stations: list[MeasuredStation] = []
    context_inputs: list[StationContextInput] = []

    for s_id, s in stations.items():
        pos = get_pos(s_id)
        if not pos:
            continue

        visual_state = build_station_visual_state(s_id, s, lines, skip_map, styles)
        facility_tags = collect_facility_tags(s) if badges_enabled else []
        station_fonts = resolve_station_fonts(
            font_paths,
            styles,
            is_tram_station=visual_state.is_tram_station,
        )
        line_markers = station_markers.get(s_id, [])
        badge_metrics = measure_badges(
            draw,
            line_markers,
            facility_tags,
            font_paths,
            scale_factor,
        )
        text_metrics = measure_label_text(
            draw,
            s_id,
            s,
            station_fonts,
            scale_factor,
            badge_metrics.primary.width,
            badge_metrics.primary.height,
        )

        symbol: StationSymbol | None = None
        axis_dir: tuple[int, int] | None = None
        station_line_ids = [str(lid) for lid in s.get("lines", [])]
        axis = _choose_station_axis(
            pos, station_line_ids, line_polylines, segment_map, bundle_offsets
        )
        if axis is not None:
            normal, key, laterals = axis
            symbol_pos: tuple[float, float] = (float(pos[0]), float(pos[1]))
            span = (max(laterals) - min(laterals)) if laterals else 0.0
            direction = (key[1][0] - key[0][0], key[1][1] - key[0][1])
            axis_dir = (
                (0 if direction[0] == 0 else (1 if direction[0] > 0 else -1)),
                (0 if direction[1] == 0 else (1 if direction[1] > 0 else -1)),
            )
            offset_magnitude = max((abs(value) for value in laterals), default=0.0)
            if span < 1e-6 and offset_magnitude < 1e-6:
                corner_radius = float(styles.get("CORNER_RADIUS", 0.0))
                line_width = float(styles["LINE_WIDTH"])
                ring_radius = float(
                    styles.get("TRANSFER_RING_RADIUS", line_width * 0.55)
                )
                ring_stroke = float(
                    styles.get("TRANSFER_RING_STROKE", line_width * 0.16)
                )
                junction = None
                if visual_state.is_transfer:
                    # no parallel bundle here, but the lines may still fan
                    # out along one direction once their corners are cut
                    junction = fit_junction_spread(
                        (float(pos[0]), float(pos[1])),
                        _station_track_points(
                            pos,
                            station_line_ids,
                            strokes_by_line,
                            search_radius=line_width * 3.0,
                        ),
                        tolerance=line_width * 0.35,
                        # a ring only reads as one interchange while every
                        # track's centreline still falls inside its core
                        min_span=(ring_radius - ring_stroke) * 2.0,
                    )
                if junction is not None:
                    normal, laterals = junction
                else:
                    corner_pose = _corner_symbol_pose(
                        pos,
                        station_line_ids,
                        line_polylines,
                        corner_radius,
                    )
                    if corner_pose is not None:
                        symbol_pos, normal, axis_dir = corner_pose
                        laterals = [0.0]
            symbol = build_station_symbol(
                symbol_pos,
                is_transfer=visual_state.is_transfer,
                normal=normal,
                laterals=laterals,
                styles=styles,
            )

        measured_stations.append(
            MeasuredStation(
                station_id=s_id,
                station=s,
                pos=pos,
                visual_state=visual_state,
                station_fonts=station_fonts,
                badge_variant=badge_metrics,
                text_variant=text_metrics,
                symbol=symbol,
                axis_dir=axis_dir,
            )
        )
        context_inputs.append(
            StationContextInput(
                station_id=s_id,
                pos=pos,
                block_width=text_metrics.primary.block_width,
                block_height=text_metrics.primary.block_height,
                is_transfer=visual_state.is_transfer,
                has_badges=bool(line_markers or facility_tags),
                name_length=len(text_metrics.primary.name_cn),
            )
        )

    local_contexts = build_local_label_contexts(context_inputs, scale_factor)
    label_boxes: list[tuple[float, float, float, float]] = []

    symbol_boxes: dict[str, tuple[float, float, float, float]] = {
        item.station_id: item.symbol.bbox
        for item in measured_stations
        if item.symbol is not None
    }
    line_width = float(styles["LINE_WIDTH"])
    segment_extents: dict[tuple[tuple[int, int], tuple[int, int]], float] = {}
    for key, member_lines in segment_map.items():
        laterals = [
            abs(float(bundle_offsets.get((lid, key), 0.0))) for lid in member_lines
        ]
        segment_extents[key] = (max(laterals) if laterals else 0.0) + line_width / 2.0

    def station_sort_key(
        item: MeasuredStation,
    ) -> tuple[int, int, int, int, float, str]:
        context = local_contexts.get(item.station_id)
        dense_rank = 0 if context and context.dense else 1
        cluster_rank = (
            context.cluster_id if context and context.cluster_id is not None else 999999
        )
        corridor_rank = context.corridor_index if context else 999999
        transfer_rank = 0 if item.visual_state.is_transfer else 1
        block_rank = -max(
            item.text_variant.primary.block_width,
            item.text_variant.primary.block_height,
        )
        return (
            dense_rank,
            cluster_rank,
            corridor_rank,
            transfer_rank,
            block_rank,
            item.station_id,
        )

    for measured in sorted(measured_stations, key=station_sort_key):
        s_id = measured.station_id
        s = measured.station
        pos = measured.pos
        visual_state = measured.visual_state
        station_fonts = measured.station_fonts
        badge_variant = measured.badge_variant
        text_variant = measured.text_variant
        text_metrics = text_variant.primary

        if measured.symbol is not None:
            render_station_symbol(draw, measured.symbol, styles)
        else:
            draw.ellipse(
                [
                    pos[0] - visual_state.radius,
                    pos[1] - visual_state.radius,
                    pos[0] + visual_state.radius,
                    pos[1] + visual_state.radius,
                ],
                fill=str(styles.get("COLOR_BG", "#FAFAF7")),
                outline=visual_state.stroke_color,
                width=int(float(visual_state.stroke_width)),
            )

        line_markers = station_markers.get(s_id, [])
        facility_tags = collect_facility_tags(s) if badges_enabled else []

        label_offset_base = float(styles["LABEL_OFFSET_BASE"])
        collision_segments = (
            tram_line_segments_for_collision
            if visual_state.is_tram_station
            else line_segments_for_collision
        )
        obstacle_boxes = [box for sid, box in symbol_boxes.items() if sid != s_id]
        placement = place_label_block(
            pos,
            text_metrics.block_width,
            text_metrics.block_height,
            collision_segments,
            label_boxes,
            label_offset_base,
            scale_factor,
            local_context=local_contexts.get(s_id),
            axis_dir=measured.axis_dir,
            obstacle_boxes=obstacle_boxes,
            segment_extents=segment_extents,
            soft_line_segments=(
                soft_line_segments if not visual_state.is_tram_station else []
            ),
        )

        effective_line_markers = line_markers
        effective_facility_tags = facility_tags

        label_boxes.append(placement.box)
        bx = placement.x
        by = placement.y
        # right-align text whenever the block sits mostly left of the
        # station, so the (usually narrower) CJK title hugs its anchor
        align_right = (placement.box[0] + placement.box[2]) / 2.0 < pos[0]

        context = local_contexts.get(s_id)
        if context and context.dense:
            leader = compute_leader_line(
                pos,
                placement.box,
                visual_state.radius,
                scale_factor,
            )
            if leader is not None:
                draw.line(
                    [leader[0], leader[1]],
                    fill=str(
                        styles.get("COLOR_GUIDE_LINE", styles["COLOR_LEGEND_BORDER"])
                    ),
                    width=1,
                )

        title_x = (
            bx
            if not align_right
            else bx + (text_metrics.block_width - text_metrics.width_cn)
        )
        draw.text(
            (title_x, by),
            text_metrics.name_cn,
            fill=visual_state.text_color_main,
            font=station_fonts.cn,
        )

        if text_metrics.name_en and text_metrics.english_y_offset is not None:
            en_x = (
                bx
                if not align_right
                else bx + (text_metrics.block_width - text_metrics.width_en)
            )
            draw.text(
                (en_x, by + text_metrics.english_y_offset),
                text_metrics.name_en,
                fill=visual_state.text_color_sub,
                font=station_fonts.en,
            )

        if effective_line_markers or effective_facility_tags:
            marker_start_x = bx if not align_right else bx + text_metrics.block_width
            box_h = float(9 * scale_factor)
            inactive_color = str(styles["COLOR_INACTIVE"])
            marker_y = by + (text_metrics.badges_y_offset or 0.0)
            draw_badges(
                draw,
                marker_start_x,
                marker_y,
                effective_line_markers,
                effective_facility_tags,
                font_paths,
                scale_factor,
                inactive_color,
                align="right" if align_right else "left",
            )
