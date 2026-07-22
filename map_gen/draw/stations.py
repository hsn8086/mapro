from __future__ import annotations

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
from ..station_symbols import (
    StationSymbol,
    build_station_symbol,
    find_station_axes,
    render_station_symbol,
)

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
_TOILET_INSIDE_PATH = os.path.join(_ASSETS_DIR, "toilet_inside.png")
_TOILET_OUTSIDE_PATH = os.path.join(_ASSETS_DIR, "toilet_outside.png")
TOILET_ICON_INSIDE: Image.Image | None = None
TOILET_ICON_OUTSIDE: Image.Image | None = None


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
) -> None:
    global TOILET_ICON_INSIDE, TOILET_ICON_OUTSIDE
    line_polylines = line_polylines or {}
    segment_map = segment_map or {}
    bundle_offsets = bundle_offsets or {}
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
            symbol = build_station_symbol(
                pos,
                is_transfer=visual_state.is_transfer,
                normal=normal,
                laterals=laterals,
                styles=styles,
            )
            direction = (key[1][0] - key[0][0], key[1][1] - key[0][1])
            axis_dir = (
                (0 if direction[0] == 0 else (1 if direction[0] > 0 else -1)),
                (0 if direction[1] == 0 else (1 if direction[1] > 0 else -1)),
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
        )

        effective_line_markers = line_markers
        effective_facility_tags = facility_tags

        label_boxes.append(placement.box)
        bx = placement.x
        by = placement.y
        align_right = placement.box[2] <= pos[0]

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
