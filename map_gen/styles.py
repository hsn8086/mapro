from __future__ import annotations


def build_style_constants(scale_factor: int) -> dict[str, float | str]:
    line_width = 8.0 * scale_factor
    return {
        "LINE_WIDTH": line_width,
        # flat cartography palette: warm paper + one ink + grey ramp
        "COLOR_BG": "#FAFAF7",
        "COLOR_TEXT_MAIN": "#1A1A1A",
        "COLOR_TEXT_SUB": "#8A8A8A",
        "COLOR_INK": "#1A1A1A",
        "COLOR_STATION_STROKE": "#1A1A1A",
        "COLOR_LEGEND_BORDER": "#DEDEDA",
        "COLOR_GUIDE_LINE": "#DEDEDA",
        "COLOR_INACTIVE": "#D8D8D4",
        "COLOR_STATUS_PLANNED": "#D8D8D4",
        "COLOR_STATUS_UNDER_CONSTRUCTION": "#B8B8B4",
        "COLOR_INACTIVE_STROKE": "#C4C4C0",
        "COLOR_CONNECTION_PHYSICAL": "#8A8A8A",
        "COLOR_CONNECTION_VIRTUAL": "#B8B8B4",
        "COLOR_CONNECTION_BUS": "#8A8A8A",
        # bundle geometry (W = LINE_WIDTH)
        "BUNDLE_GAP": line_width * 0.15,
        "BUNDLE_MIN_RUN": line_width * 5.0,
        "BUNDLE_CONNECTOR_MAX": line_width * 12.0,
        "CORNER_RADIUS": line_width * 1.25,
        # station symbols
        "STATION_DOT_RADIUS": line_width * 0.26,
        "STATION_SLOT_WIDTH": line_width * 0.35,
        "STATION_SLOT_BREADTH": line_width * 0.55,
        "TRANSFER_RING_RADIUS": line_width * 0.55,
        "TRANSFER_RING_STROKE": max(1.0, line_width * 0.16),
        # kept for legacy consumers (leader lines, sort keys)
        "STATION_RADIUS_NORMAL": line_width * 0.28,
        "STATION_RADIUS_TRANSFER": line_width * 0.55,
        "STATION_STROKE": 1.5 * scale_factor,
        "STATION_STROKE_TRANSFER": max(1.0, line_width * 0.16),
        "FONT_SIZE_LABEL": 12 * scale_factor,
        "FONT_SIZE_LABEL_EN": 6 * scale_factor,
        "FONT_SIZE_TITLE": 28 * scale_factor,
        "FONT_SIZE_SUBTITLE": 14 * scale_factor,
        "LABEL_OFFSET_BASE": 10 * scale_factor,
        "LABEL_OFFSET_DIAG": 22 * scale_factor,
    }


def is_non_active_status(status: str) -> bool:
    return str(status or "active") != "active"


def resolve_status_color(
    status: str,
    styles: dict[str, float | str],
    *,
    active_color: str,
) -> str:
    normalized = str(status or "active")
    if normalized == "active":
        return active_color
    if normalized == "planned":
        return str(
            styles.get(
                "COLOR_STATUS_PLANNED", styles.get("COLOR_INACTIVE", active_color)
            )
        )
    if normalized == "under_construction":
        return str(
            styles.get(
                "COLOR_STATUS_UNDER_CONSTRUCTION",
                styles.get("COLOR_INACTIVE", active_color),
            )
        )
    return str(styles.get("COLOR_INACTIVE", active_color))
