from __future__ import annotations

import colorsys


def _parse_hex_color(color: str) -> tuple[float, float, float] | None:
    text = color.strip().lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6:
        return None
    try:
        red = int(text[0:2], 16) / 255.0
        green = int(text[2:4], 16) / 255.0
        blue = int(text[4:6], 16) / 255.0
    except ValueError:
        return None
    return (red, green, blue)


def normalize_line_color(
    color: str,
    *,
    saturation_range: tuple[float, float] = (0.55, 0.85),
    lightness_range: tuple[float, float] = (0.38, 0.58),
) -> str:
    """Clamp a line colour into a harmonised saturation/lightness band.

    Hue is preserved; only S and L are clamped so official line colours stay
    recognisable while the overall map keeps an even tonal weight. Invalid
    input is returned unchanged.
    """
    rgb = _parse_hex_color(color)
    if rgb is None:
        return color

    hue, lightness, saturation = colorsys.rgb_to_hls(*rgb)
    if saturation <= 1e-9:  # pure greys carry no hue to preserve
        return color

    saturation = min(max(saturation, saturation_range[0]), saturation_range[1])
    lightness = min(max(lightness, lightness_range[0]), lightness_range[1])
    red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
    return "#%02x%02x%02x" % (round(red * 255), round(green * 255), round(blue * 255))
