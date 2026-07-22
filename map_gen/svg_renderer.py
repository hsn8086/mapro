from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .render_pipeline import draw_render_plan
from .render_plan import build_render_plan


def _fmt(value: float) -> str:
    rounded = round(float(value), 3)
    if rounded == int(rounded):
        return str(int(rounded))
    return str(rounded).rstrip("0").rstrip(".")


def _attr(value: object) -> str:
    return escape(str(value), quote=True)


def _text(value: object) -> str:
    return escape(str(value), quote=False)


def _color(value: str | None) -> str:
    return "none" if value is None else str(value)


def _font_size(font: object, fallback: float) -> float:
    size = getattr(font, "size", None)
    if isinstance(size, int | float):
        return float(size)
    return fallback


def _font_weight(font: object) -> str | None:
    get_name = getattr(font, "getname", None)
    if not callable(get_name):
        return None
    try:
        name = " ".join(str(part) for part in get_name())
    except Exception:
        return None
    return "700" if "bold" in name.lower() else None


class SvgCanvas:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.elements: list[str] = []
        self.draw = SvgDraw(self)

    def add(self, element: str) -> None:
        self.elements.append(element)

    def to_svg(self) -> str:
        font_family = "Noto Sans CJK SC, Noto Sans CJK, Microsoft YaHei, sans-serif"
        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" '
            f'height="{self.height}" viewBox="0 0 {self.width} {self.height}">',
            f'<g font-family="{_attr(font_family)}" shape-rendering="geometricPrecision">',
            f'<rect x="0" y="0" width="{self.width}" height="{self.height}" fill="white" />',
            *self.elements,
            "</g>",
            "</svg>",
        ]
        return "\n".join(lines)

    def save(self, output_path: str) -> None:
        Path(output_path).write_text(self.to_svg(), encoding="utf-8")


class SvgDraw:
    def __init__(self, canvas: SvgCanvas) -> None:
        self.canvas = canvas
        measure_image = Image.new("RGB", (1, 1), "white")
        self._measure_draw = ImageDraw.Draw(measure_image)

    def textbbox(
        self,
        position: tuple[float, float],
        text: str,
        font: ImageFont.ImageFont
        | ImageFont.FreeTypeFont
        | ImageFont.TransposedFont
        | None = None,
    ) -> tuple[float, float, float, float]:
        bbox = self._measure_draw.textbbox(position, text, font=font)
        return (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))

    def text(
        self,
        position: tuple[float, float],
        text: str,
        *,
        fill: str,
        font: ImageFont.ImageFont | ImageFont.FreeTypeFont | ImageFont.TransposedFont,
    ) -> None:
        bbox = self.textbbox((0, 0), text, font=font)
        fallback_size = max(1.0, float(bbox[3] - bbox[1]))
        font_size = _font_size(font, fallback_size)
        weight = _font_weight(font)
        weight_attr = f' font-weight="{weight}"' if weight is not None else ""
        self.canvas.add(
            "<text "
            f'x="{_fmt(position[0])}" y="{_fmt(position[1])}" '
            f'font-size="{_fmt(font_size)}" fill="{_attr(fill)}"{weight_attr} '
            'dominant-baseline="text-before-edge">'
            f"{_text(text)}</text>"
        )

    def line(
        self,
        points: list[tuple[float, float]],
        *,
        fill: str,
        width: int | float,
        joint: str | None = None,
    ) -> None:
        _ = joint
        if len(points) < 2:
            return
        point_list = " ".join(f"{_fmt(x)},{_fmt(y)}" for x, y in points)
        self.canvas.add(
            "<polyline "
            f'points="{_attr(point_list)}" fill="none" stroke="{_attr(fill)}" '
            f'stroke-width="{_fmt(width)}" stroke-linecap="round" stroke-linejoin="round" />'
        )

    def path(
        self,
        d: str,
        *,
        fill: str | None = None,
        stroke: str | None = None,
        stroke_width: int | float = 1,
        stroke_linecap: str | None = None,
        stroke_linejoin: str | None = None,
    ) -> None:
        linecap_attr = (
            f' stroke-linecap="{_attr(stroke_linecap)}"'
            if stroke_linecap is not None
            else ""
        )
        linejoin_attr = (
            f' stroke-linejoin="{_attr(stroke_linejoin)}"'
            if stroke_linejoin is not None
            else ""
        )
        self.canvas.add(
            "<path "
            f'd="{_attr(d)}" fill="{_attr(_color(fill))}" '
            f'stroke="{_attr(_color(stroke))}" stroke-width="{_fmt(stroke_width)}"'
            f"{linecap_attr}{linejoin_attr} />"
        )

    def polygon(
        self,
        points: list[tuple[float, float]],
        *,
        fill: str | None = None,
    ) -> None:
        if len(points) < 3:
            return
        point_list = " ".join(f"{_fmt(x)},{_fmt(y)}" for x, y in points)
        self.canvas.add(
            f'<polygon points="{_attr(point_list)}" fill="{_attr(_color(fill))}" />'
        )

    def ellipse(
        self,
        bounds: list[float],
        *,
        fill: str | None = None,
        outline: str | None = None,
        width: int | float = 1,
    ) -> None:
        left, top, right, bottom = bounds
        cx = (left + right) / 2
        cy = (top + bottom) / 2
        rx = abs(right - left) / 2
        ry = abs(bottom - top) / 2
        self.canvas.add(
            "<ellipse "
            f'cx="{_fmt(cx)}" cy="{_fmt(cy)}" rx="{_fmt(rx)}" ry="{_fmt(ry)}" '
            f'fill="{_attr(_color(fill))}" stroke="{_attr(_color(outline))}" '
            f'stroke-width="{_fmt(width)}" />'
        )

    def rectangle(
        self,
        bounds: list[float],
        *,
        fill: str | None = None,
        outline: str | None = None,
        width: int | float = 1,
    ) -> None:
        left, top, right, bottom = bounds
        self.canvas.add(
            "<rect "
            f'x="{_fmt(left)}" y="{_fmt(top)}" '
            f'width="{_fmt(right - left)}" height="{_fmt(bottom - top)}" '
            f'fill="{_attr(_color(fill))}" stroke="{_attr(_color(outline))}" '
            f'stroke-width="{_fmt(width)}" />'
        )

    def rounded_rectangle(
        self,
        bounds: tuple[float, float, float, float] | list[float],
        *,
        fill: str | None = None,
        radius: int | float = 0,
        outline: str | None = None,
        width: int | float = 1,
    ) -> None:
        left, top, right, bottom = bounds
        self.canvas.add(
            "<rect "
            f'x="{_fmt(left)}" y="{_fmt(top)}" '
            f'width="{_fmt(right - left)}" height="{_fmt(bottom - top)}" '
            f'rx="{_fmt(radius)}" ry="{_fmt(radius)}" '
            f'fill="{_attr(_color(fill))}" stroke="{_attr(_color(outline))}" '
            f'stroke-width="{_fmt(width)}" />'
        )


def render_svg_string(
    data: dict[str, Any],
    font_paths: list[str] | None = None,
    *,
    badges_enabled: bool = True,
) -> str:
    plan = build_render_plan(data, font_paths, badges_enabled=badges_enabled)
    canvas = SvgCanvas(plan.layout.width, plan.layout.height)
    draw_render_plan(plan, canvas, canvas.draw)
    return canvas.to_svg()


def draw_metro_map_svg(
    data: dict[str, Any],
    output_path: str,
    bg_path: str | None = None,
    font_paths: list[str] | None = None,
    *,
    badges_enabled: bool = True,
) -> None:
    _ = bg_path
    plan = build_render_plan(data, font_paths, badges_enabled=badges_enabled)
    canvas = SvgCanvas(plan.layout.width, plan.layout.height)
    draw_render_plan(plan, canvas, canvas.draw)
    canvas.save(output_path)
    print(f"Saved to {output_path}")
