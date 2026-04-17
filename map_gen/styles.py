from __future__ import annotations


def build_style_constants(scale_factor: int) -> dict[str, float | str]:
    return {
        "LINE_WIDTH": 9 * scale_factor,
        "COLOR_TEXT_MAIN": "#2c3e50",
        "COLOR_TEXT_SUB": "#95a5a6",
        "COLOR_STATION_STROKE": "#34495e",
        "COLOR_LEGEND_BORDER": "#bdc3c7",
        "COLOR_INACTIVE": "#ecf0f1",
        "COLOR_INACTIVE_STROKE": "#bdc3c7",
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
