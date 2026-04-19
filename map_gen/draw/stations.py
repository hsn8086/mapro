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

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
_TOILET_INSIDE_PATH = os.path.join(_ASSETS_DIR, "toilet_inside.png")
_TOILET_OUTSIDE_PATH = os.path.join(_ASSETS_DIR, "toilet_outside.png")
TOILET_ICON_INSIDE: Image.Image | None = None
TOILET_ICON_OUTSIDE: Image.Image | None = None


@dataclass(frozen=True)
class MeasuredStation:
    station_id: str
    station: dict
    pos: tuple[int, int]
    visual_state: StationVisualState
    station_fonts: StationFonts
    badge_variant: BadgeVariant
    text_variant: LabelTextVariant


def draw_stations(
    img,
    draw,
    stations: dict,
    lines: dict,
    get_pos,
    skip_map: set[tuple[str, str]],
    station_markers: dict[str, list[dict]],
    line_segments_for_collision: list[tuple[tuple[int, int], tuple[int, int]]],
    scale_factor: int,
    font_paths: list[str],
    styles: dict[str, float | str],
) -> None:
    global TOILET_ICON_INSIDE, TOILET_ICON_OUTSIDE
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
        facility_tags = collect_facility_tags(s)
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

        measured_stations.append(
            MeasuredStation(
                station_id=s_id,
                station=s,
                pos=pos,
                visual_state=visual_state,
                station_fonts=station_fonts,
                badge_variant=badge_metrics,
                text_variant=text_metrics,
            )
        )
        context_inputs.append(
            StationContextInput(
                station_id=s_id,
                pos=pos,
                block_width=text_metrics.core.block_width,
                block_height=text_metrics.core.block_height,
                is_transfer=visual_state.is_transfer,
                has_badges=bool(line_markers or facility_tags),
                name_length=len(text_metrics.primary.name_cn),
            )
        )

    local_contexts = build_local_label_contexts(context_inputs, scale_factor)
    label_boxes: list[tuple[float, float, float, float]] = []

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
            item.text_variant.core.block_width,
            item.text_variant.core.block_height,
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
        draw.ellipse(
            [
                pos[0] - visual_state.radius,
                pos[1] - visual_state.radius,
                pos[0] + visual_state.radius,
                pos[1] + visual_state.radius,
            ],
            fill="white",
            outline=visual_state.stroke_color,
            width=int(float(visual_state.stroke_width)),
        )

        line_markers = station_markers.get(s_id, [])
        facility_tags = collect_facility_tags(s)

        label_offset_base = float(styles["LABEL_OFFSET_BASE"])
        base_placement = place_label_block(
            pos,
            text_metrics.block_width,
            text_metrics.block_height,
            line_segments_for_collision,
            label_boxes,
            label_offset_base,
            scale_factor,
            local_context=local_contexts.get(s_id),
        )

        placement = base_placement

        effective_line_markers = line_markers
        effective_facility_tags = facility_tags
        if local_contexts.get(s_id) and local_contexts[s_id].dense:
            text_metrics = text_variant.core
            core_placement = place_label_block(
                pos,
                text_metrics.block_width,
                text_metrics.block_height,
                line_segments_for_collision,
                label_boxes,
                label_offset_base,
                scale_factor,
                local_context=local_contexts.get(s_id),
            )
            placement = core_placement
            candidates: list[
                tuple[
                    float,
                    LabelTextMetrics,
                    BadgeMetrics,
                    list[dict],
                    list[str],
                    LabelPlacement,
                ]
            ] = []

            candidates.append(
                (
                    core_placement.score,
                    text_variant.core,
                    badge_variant.compact,
                    [],
                    [],
                    core_placement,
                )
            )

            full_text = text_variant.primary
            full_badges = badge_variant.primary
            full_placement = place_label_block(
                pos,
                full_text.block_width,
                full_text.block_height,
                line_segments_for_collision,
                label_boxes,
                label_offset_base,
                scale_factor,
                local_context=local_contexts.get(s_id),
            )
            candidates.append(
                (
                    full_placement.score + 0.08,
                    full_text,
                    full_badges,
                    line_markers,
                    facility_tags,
                    full_placement,
                )
            )

            if text_variant.primary.name_en:
                compact_text = text_variant.compact
                compact_placement = place_label_block(
                    pos,
                    compact_text.block_width,
                    compact_text.block_height,
                    line_segments_for_collision,
                    label_boxes,
                    label_offset_base,
                    scale_factor,
                    local_context=local_contexts.get(s_id),
                )
                candidates.append(
                    (
                        compact_placement.score + 0.18,
                        compact_text,
                        full_badges,
                        line_markers,
                        facility_tags,
                        compact_placement,
                    )
                )

            if line_markers or facility_tags:
                badge_free_text = measure_label_text(
                    draw,
                    s_id,
                    s,
                    station_fonts,
                    scale_factor,
                    badge_variant.compact.width,
                    badge_variant.compact.height,
                ).primary
                badge_free_placement = place_label_block(
                    pos,
                    badge_free_text.block_width,
                    badge_free_text.block_height,
                    line_segments_for_collision,
                    label_boxes,
                    label_offset_base,
                    scale_factor,
                    local_context=local_contexts.get(s_id),
                )
                candidates.append(
                    (
                        badge_free_placement.score + 0.28,
                        badge_free_text,
                        badge_variant.compact,
                        [],
                        [],
                        badge_free_placement,
                    )
                )

                if text_variant.primary.name_en:
                    badge_free_compact = measure_label_text(
                        draw,
                        s_id,
                        s,
                        station_fonts,
                        scale_factor,
                        badge_variant.compact.width,
                        badge_variant.compact.height,
                    ).compact
                    badge_free_compact_placement = place_label_block(
                        pos,
                        badge_free_compact.block_width,
                        badge_free_compact.block_height,
                        line_segments_for_collision,
                        label_boxes,
                        label_offset_base,
                        scale_factor,
                        local_context=local_contexts.get(s_id),
                    )
                    candidates.append(
                        (
                            badge_free_compact_placement.score + 0.42,
                            badge_free_compact,
                            badge_variant.compact,
                            [],
                            [],
                            badge_free_compact_placement,
                        )
                    )

            best = min(candidates, key=lambda item: item[0])
            chosen_text = best[1]
            chosen_line_markers = best[3]
            chosen_facility_tags = best[4]

            # 主标签位置永远由 core placement 决定，只允许在其下附着次要信息。
            # 这样无论密集区怎么退让，都不会出现“主标签实际缺席”的情况。
            if chosen_text is not text_variant.core:
                horizontal_shift = best[5].x - core_placement.x
                vertical_shift = best[5].y - core_placement.y
                if abs(horizontal_shift) <= 24 * scale_factor:
                    placement = LabelPlacement(
                        x=core_placement.x,
                        y=core_placement.y,
                        box=(
                            core_placement.box[0],
                            core_placement.box[1],
                            core_placement.box[0] + chosen_text.block_width,
                            core_placement.box[1] + chosen_text.block_height,
                        ),
                        score=best[0] + 0.02,
                    )
                elif abs(vertical_shift) <= 24 * scale_factor:
                    placement = LabelPlacement(
                        x=core_placement.x,
                        y=core_placement.y,
                        box=(
                            core_placement.box[0],
                            core_placement.box[1],
                            core_placement.box[0] + chosen_text.block_width,
                            core_placement.box[1] + chosen_text.block_height,
                        ),
                        score=best[0] + 0.04,
                    )
                else:
                    placement = best[5]
            text_metrics = chosen_text
            effective_line_markers = chosen_line_markers
            effective_facility_tags = chosen_facility_tags

        label_boxes.append(placement.box)
        bx = placement.x
        by = placement.y

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

        draw.text(
            (bx, by),
            text_metrics.name_cn,
            fill=visual_state.text_color_main,
            font=station_fonts.cn,
        )

        if text_metrics.name_en and text_metrics.english_y_offset is not None:
            draw.text(
                (bx, by + text_metrics.english_y_offset),
                text_metrics.name_en,
                fill=visual_state.text_color_sub,
                font=station_fonts.en,
            )

        if effective_line_markers or effective_facility_tags:
            marker_start_x = bx
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
            )
