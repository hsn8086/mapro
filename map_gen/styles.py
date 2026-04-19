from __future__ import annotations


def build_style_constants(scale_factor: int) -> dict[str, float | str]:
    return {
        "LINE_WIDTH": 9 * scale_factor,
        "COLOR_TEXT_MAIN": "#2c3e50",
        "COLOR_TEXT_SUB": "#95a5a6",
        "COLOR_STATION_STROKE": "#34495e",
        "COLOR_LEGEND_BORDER": "#bdc3c7",
        "COLOR_GUIDE_LINE": "#c7d0d9",
        "COLOR_INACTIVE": "#ecf0f1",
        "COLOR_STATUS_PLANNED": "#d9e1ea",
        "COLOR_STATUS_UNDER_CONSTRUCTION": "#d9c6a6",
        "COLOR_INACTIVE_STROKE": "#bdc3c7",
        "COLOR_CONNECTION_PHYSICAL": "#7f8c8d",
        "COLOR_CONNECTION_VIRTUAL": "#95a5a6",
        "COLOR_CONNECTION_BUS": "#e67e22",
        "STATION_RADIUS_NORMAL": 3.5 * scale_factor,
        "STATION_RADIUS_TRANSFER": 6 * scale_factor,
        "STATION_STROKE": 1.5 * scale_factor,
        "STATION_STROKE_TRANSFER": 2.5 * scale_factor,
        "FONT_SIZE_LABEL": 13 * scale_factor,
        "FONT_SIZE_LABEL_EN": 6 * scale_factor,
        "FONT_SIZE_TITLE": 42 * scale_factor,
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
        return str(styles.get("COLOR_STATUS_PLANNED", styles.get("COLOR_INACTIVE", active_color)))
    if normalized == "under_construction":
        return str(
            styles.get(
                "COLOR_STATUS_UNDER_CONSTRUCTION",
                styles.get("COLOR_INACTIVE", active_color),
            )
        )
    return str(styles.get("COLOR_INACTIVE", active_color))
