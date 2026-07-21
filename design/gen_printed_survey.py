"""Printed Survey — positive print of a fictional transit lattice on archival paper.

Renders a museum-grade PNG. All geometry is procedural; no real city.
Ink accumulates multiplicatively, like overprinting on paper.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- config

FONT_DIR = Path("/home/small-hsn/.agents/skills/canvas-design/canvas-fonts")
OUT = Path("/home/small-hsn/projects/mapro/design/printed_survey.png")

SS = 2  # supersample
W, H = 3200 * SS, 4000 * SS

PAPER = (243, 240, 232)  # F3F0E8 warm archival stock
INK = (30, 30, 33)  # carbon grey-black
RED = (188, 70, 44)  # oxidised vermilion (surveyor's mark)
BLUE = (72, 102, 124)  # faded prussian
GRIDC = (188, 181, 167)  # reseau etch
NOTE = (118, 113, 102)  # annotation grey

rng = random.Random(20260721)

# world coordinates: x in [0,100], y in [0,125]; y up
WX, WY = 100.0, 125.0
MARG_X = 0.105
PLATE_TOP = 0.075
PLATE_BOT = 0.155
PX0 = W * MARG_X
PX1 = W * (1 - MARG_X)
PY0 = H * PLATE_TOP
PY1 = H * (1 - PLATE_BOT)


def to_px(x: float, y: float) -> tuple[float, float]:
    return (
        PX0 + (x / WX) * (PX1 - PX0),
        PY1 - (y / WY) * (PY1 - PY0),
    )


# ---------------------------------------------------------------- network

LINES: dict[str, list[tuple[float, float]]] = {
    "A": [(10, 78), (34, 78), (46, 90), (66, 90), (78, 78), (92, 78)],
    "B": [(56, 116), (56, 88), (48, 80), (48, 40), (58, 30), (58, 12)],
    "C": [(32, 66), (32, 94), (42, 104), (64, 104), (76, 92), (76, 72), (64, 66)],
    "D": [(12, 108), (40, 80), (40, 68), (62, 46), (62, 30)],
    "E": [(14, 30), (38, 30), (50, 42), (76, 42), (88, 30)],
    "F": [(18, 90), (30, 102), (52, 112), (70, 112)],
    "G": [(24, 94), (24, 46), (34, 36), (34, 20)],
    "H": [(86, 98), (86, 64), (72, 50), (72, 34)],
}
RIVER = (50.0, 63.0)  # y-band kept free of stations
SPACING = 4.6


def seg_points(
    a: tuple[float, float], b: tuple[float, float]
) -> list[tuple[float, float]]:
    ax, ay = a
    bx, by = b
    d = math.hypot(bx - ax, by - ay)
    n = max(1, round(d / SPACING))
    return [(ax + (bx - ax) * i / n, ay + (by - ay) * i / n) for i in range(1, n)]


def build() -> tuple[
    dict[tuple[float, float], set[str]], dict[str, list[tuple[float, float]]]
]:
    raw: dict[str, list[tuple[float, float]]] = {}
    for lid, wps in LINES.items():
        pts: list[tuple[float, float]] = [wps[0]]
        for a, b in zip(wps, wps[1:]):
            pts.extend(seg_points(a, b))
            pts.append(b)
        pts = [p for p in pts if not (RIVER[0] < p[1] < RIVER[1])]
        raw[lid] = pts
    merged: list[tuple[float, float]] = []
    station_lines: dict[int, set[str]] = {}
    line_station_idx: dict[str, list[int]] = {}
    for lid, pts in raw.items():
        idxs = []
        for p in pts:
            found = -1
            for i, q in enumerate(merged):
                if math.hypot(p[0] - q[0], p[1] - q[1]) < 2.6:
                    found = i
                    break
            if found < 0:
                merged.append(p)
                found = len(merged) - 1
                station_lines[found] = set()
            station_lines[found].add(lid)
            if not idxs or idxs[-1] != found:
                idxs.append(found)
        line_station_idx[lid] = idxs
    stations = {merged[i]: station_lines[i] for i in range(len(merged))}
    per_line = {
        lid: [merged[i] for i in idxs] for lid, idxs in line_station_idx.items()
    }
    return stations, per_line


# ---------------------------------------------------------------- ink layer


def ink_sprite(radius_px: float, size: int) -> np.ndarray:
    """Solid dot with a tight ink-bleed fringe."""
    ax = np.arange(size) - (size - 1) / 2
    xx, yy = np.meshgrid(ax, ax)
    rr = np.sqrt(xx * xx + yy * yy)
    core = np.clip(1.0 - (rr - radius_px * 0.72) / (radius_px * 0.5), 0, 1)
    bleed = np.exp(-((rr / (radius_px * 1.7)) ** 2)) * 0.12
    return np.clip(core + bleed, 0, 1)


def add_sprite(
    buf: np.ndarray, x: float, y: float, spr: np.ndarray, gain: float
) -> None:
    s = spr.shape[0]
    x0 = int(round(x - s / 2))
    y0 = int(round(y - s / 2))
    x1, y1 = x0 + s, y0 + s
    if x1 < 0 or y1 < 0 or x0 >= buf.shape[1] or y0 >= buf.shape[0]:
        return
    sx0, sy0 = max(0, -x0), max(0, -y0)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(buf.shape[1], x1), min(buf.shape[0], y1)
    buf[y0:y1, x0:x1] += spr[sy0 : sy0 + (y1 - y0), sx0 : sx0 + (x1 - x0)] * gain


def overprint(
    img: np.ndarray, density: np.ndarray, colour: tuple[int, int, int], strength: float
) -> None:
    """Multiply ink of `colour` into img with coverage `density`."""
    d = np.clip(density * strength, 0, 1)[..., None]
    ink = np.array(colour, np.float32) / 255.0
    img *= 1 - d * (1 - ink[None, None, :])


# ---------------------------------------------------------------- main render


def render() -> None:
    stations, per_line = build()
    n_objects = len(stations)
    n_transfer = sum(1 for s in stations.values() if len(s) >= 2)

    # ---- paper: uneven warm stock, faint age at the edges
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d_edge = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    tone = (
        1 - 0.030 * np.clip(d_edge - 0.45, 0, 1) ** 1.4
    )  # aged edges, never flat white
    img = np.empty((H, W, 3), np.float32)
    for c in range(3):
        img[..., c] = PAPER[c] / 255.0 * tone

    # paper fibre: fine multiplicative noise + sparse darker flecks
    fibre = 1 + (np.random.default_rng(7).standard_normal((H, W)) * 0.008).astype(
        np.float32
    )
    img *= np.clip(fibre, 0.97, 1.03)[..., None]
    fleck = np.random.default_rng(11)
    for _ in range(int(W * H / 8e5)):
        fx, fy = fleck.integers(0, W - 2), fleck.integers(0, H - 2)
        img[fy : fy + 2, fx : fx + 2] *= 0.90

    # ---- ink coverage layers
    ink_k = np.zeros((H, W), np.float32)  # carbon stars
    ink_r = np.zeros((H, W), np.float32)  # vermilion trace
    ink_b = np.zeros((H, W), np.float32)  # prussian trace

    trace_spr = ink_sprite(1.5 * SS, int(10 * SS))

    def draw_trace(pts: list[tuple[float, float]], buf: np.ndarray) -> None:
        px = [to_px(*p) for p in pts]
        for (x0, y0), (x1, y1) in zip(px, px[1:]):
            d = math.hypot(x1 - x0, y1 - y0)
            gap = 15 * SS
            if d <= 2 * gap:
                continue
            t0, t1 = gap / d, 1 - gap / d
            ax, ay = x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0
            bx, by = x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1
            steps = int(d)
            for i in range(steps + 1):
                t = i / steps
                add_sprite(buf, ax + (bx - ax) * t, ay + (by - ay) * t, trace_spr, 0.11)

    draw_trace(per_line["A"], ink_r)
    draw_trace(per_line["B"], ink_b)

    spr_cache: dict[int, np.ndarray] = {}
    for (x, y), lines_here in stations.items():
        deg = len(lines_here)
        r = {1: 3.6, 2: 6.2}.get(deg, 8.8) * SS
        r *= 1 + rng.uniform(-0.15, 0.15)
        gain = {1: 0.55, 2: 0.85}.get(deg, 1.0)
        gain *= 1 + rng.uniform(-0.12, 0.12)
        key = int(r)
        if key not in spr_cache:
            spr_cache[key] = ink_sprite(key, int(key * 5))
        px, py = to_px(x, y)
        jx = rng.uniform(-0.6, 0.6) * SS
        jy = rng.uniform(-0.6, 0.6) * SS
        add_sprite(ink_k, px + jx, py + jy, spr_cache[key], gain)

    overprint(img, ink_r, RED, 0.9)
    overprint(img, ink_b, BLUE, 0.9)
    overprint(img, ink_k, INK, 1.0)
    img = np.clip(img, 0, 1)

    canvas = Image.fromarray((img * 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(canvas, "RGBA")

    # ---- reseau grid: etched crosses at lattice intersections
    pitch = 10.0
    cross = 5 * SS
    for gx in range(0, int(WX) + 1, int(pitch)):
        for gy in range(0, int(WY) + 1, int(pitch)):
            px, py = to_px(gx, gy)
            a = (*GRIDC, 200)
            d.line([(px - cross, py), (px + cross, py)], fill=a, width=SS)
            d.line([(px, py - cross), (px, py + cross)], fill=a, width=SS)

    # plate frame
    frame = (*NOTE, 190)
    d.rectangle([PX0, PY0, PX1, PY1], outline=frame, width=SS)

    # ---- edge scales
    fnt_tick = ImageFont.truetype(str(FONT_DIR / "GeistMono-Regular.ttf"), int(26 * SS))
    tick_a = (*NOTE, 220)
    for gx in range(0, int(WX) + 1, 2):
        px, _ = to_px(gx, 0)
        long = gx % 10 == 0
        tl = (14 if long else 7) * SS
        d.line([(px, PY1), (px, PY1 + tl)], fill=tick_a, width=SS)
        d.line([(px, PY0), (px, PY0 - tl)], fill=tick_a, width=SS)
        if long:
            d.text(
                (px, PY1 + 20 * SS),
                f"{gx:03d}",
                font=fnt_tick,
                fill=(*NOTE, 235),
                anchor="ma",
            )
    for gy in range(0, int(WY) + 1, 2):
        _, py = to_px(0, gy)
        long = gy % 10 == 0
        tl = (14 if long else 7) * SS
        d.line([(PX0, py), (PX0 - tl, py)], fill=tick_a, width=SS)
        d.line([(PX1, py), (PX1 + tl, py)], fill=tick_a, width=SS)
        if long:
            d.text(
                (PX0 - 22 * SS, py),
                f"{gy:03d}",
                font=fnt_tick,
                fill=(*NOTE, 235),
                anchor="rm",
            )

    # ---- interchange rings (open ring residue of the transfer symbol)
    for (x, y), lines_here in stations.items():
        if len(lines_here) >= 3:
            px, py = to_px(x, y)
            r = 15 * SS
            d.ellipse([px - r, py - r, px + r, py + r], outline=(*INK, 150), width=SS)

    # ---- annotation: dashed circle on the densest southern cluster
    fnt_note = ImageFont.truetype(str(FONT_DIR / "GeistMono-Regular.ttf"), int(24 * SS))
    south = [p for p in stations if p[1] < RIVER[0]]
    dense = max(
        south,
        key=lambda p: sum(
            1 for q in stations if math.hypot(p[0] - q[0], p[1] - q[1]) < 10
        ),
    )
    cxp, cyp = to_px(*dense)
    rr = 60 * SS
    for ang in range(0, 360, 9):
        a0 = math.radians(ang)
        a1 = math.radians(ang + 5)
        d.line(
            [
                (cxp + rr * math.cos(a0), cyp + rr * math.sin(a0)),
                (cxp + rr * math.cos(a1), cyp + rr * math.sin(a1)),
            ],
            fill=(*NOTE, 210),
            width=SS,
        )
    d.text(
        (cxp + rr + 26 * SS, cyp),
        "cluster 04",
        font=fnt_note,
        fill=(*NOTE, 235),
        anchor="lm",
    )

    # ---- unidentified source in the river void (the only crosshair, vermilion)
    ux, uy = to_px(68, 56.5)
    arm = 20 * SS
    gapc = 7 * SS
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        d.line(
            [(ux + dx * gapc, uy + dy * gapc), (ux + dx * arm, uy + dy * arm)],
            fill=(*RED, 230),
            width=SS,
        )
    d.text(
        (ux + arm + 12 * SS, uy),
        "unidentified source",
        font=fnt_note,
        fill=(*NOTE, 235),
        anchor="lm",
    )

    # ---- typography block
    fnt_title = ImageFont.truetype(str(FONT_DIR / "Jura-Medium.ttf"), int(64 * SS))
    fnt_small = ImageFont.truetype(
        str(FONT_DIR / "GeistMono-Regular.ttf"), int(28 * SS)
    )

    def tracked(
        draw: ImageDraw.ImageDraw,
        xy: tuple[float, float],
        text: str,
        font,
        fill,
        tracking: float,
    ):
        x, y = xy
        for ch in text:
            draw.text((x, y), ch, font=font, fill=fill)
            x += draw.textlength(ch, font=font) + tracking

    ty = H * (1 - PLATE_BOT) + 70 * SS
    tracked(d, (PX0, ty + 30 * SS), "PRINTED SURVEY", fnt_title, (*INK, 245), 26 * SS)
    d.text(
        (PX0, ty + 130 * SS),
        f"{n_objects} objects · {n_transfer} interchanges · 8 traces · 2 plotted",
        font=fnt_small,
        fill=(*NOTE, 245),
    )
    d.text(
        (PX0, ty + 180 * SS),
        "schematic projection · 45° lattice · epoch 2026.5",
        font=fnt_small,
        fill=(*NOTE, 245),
    )
    d.text((PX1, ty + 30 * SS), "PLATE", font=fnt_small, fill=(*NOTE, 245), anchor="ra")
    fnt_plate = ImageFont.truetype(str(FONT_DIR / "Jura-Medium.ttf"), int(64 * SS))
    d.text((PX1, ty + 72 * SS), "01", font=fnt_plate, fill=(*INK, 245), anchor="ra")

    # ---- magnitude legend above the plate
    ly = PY0 - 48 * SS
    lx = PX0
    legend = [(3.6, "1"), (6.2, "2"), (8.8, "3+")]
    for r_w, label in legend:
        r = r_w * SS * 0.85
        d.ellipse([lx - r, ly - r, lx + r, ly + r], fill=(*INK, 235))
        d.text((lx + 16 * SS, ly), label, font=fnt_tick, fill=(*NOTE, 235), anchor="lm")
        lx += 90 * SS
    d.text(
        (lx + 6 * SS, ly),
        "lines through node",
        font=fnt_tick,
        fill=(*NOTE, 220),
        anchor="lm",
    )
    d.text((PX1, ly), "field DC-01", font=fnt_tick, fill=(*NOTE, 235), anchor="rm")

    out = canvas.resize((W // SS, H // SS), Image.LANCZOS)
    out.save(OUT)
    print("saved", OUT, "objects:", n_objects, "transfers:", n_transfer)


if __name__ == "__main__":
    render()
