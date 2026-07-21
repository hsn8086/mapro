from __future__ import annotations

from .draw.legend import draw_legend
from .draw.links import draw_transfer_connections
from .draw.lines import draw_lines
from .draw.stations import draw_stations
from .draw.title import draw_title_block
from .render_plan import RenderPlan


def draw_render_plan(plan: RenderPlan, img, draw) -> None:
    layout = plan.layout
    styles = plan.styles
    scale_factor = layout.scale_factor
    get_pos = layout.get_pos
    segment_data = plan.segment_data

    draw_lines(draw, plan.line_strokes)

    draw_transfer_connections(
        draw,
        plan.connections,
        get_pos,
        scale_factor,
        plan.font_paths,
        styles,
    )

    draw_stations(
        img,
        draw,
        plan.stations,
        plan.lines,
        get_pos,
        segment_data.skip_map,
        plan.station_markers,
        segment_data.line_segments_for_collision,
        segment_data.tram_line_segments_for_collision,
        scale_factor,
        plan.font_paths,
        styles,
        line_polylines=segment_data.line_polylines,
        segment_map=segment_data.segment_map,
        bundle_offsets=plan.bundle_offsets,
        badges_enabled=plan.badges_enabled,
    )

    draw_title_block(draw, plan.meta, plan.font_paths, styles)

    draw_legend(
        draw,
        plan.lines,
        plan.font_paths,
        scale_factor,
        layout.width,
        layout.height,
        str(styles["COLOR_TEXT_MAIN"]),
        str(styles["COLOR_LEGEND_BORDER"]),
        None,
    )
